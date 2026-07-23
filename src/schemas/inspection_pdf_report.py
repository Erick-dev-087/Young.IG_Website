"""
Inspection PDF Report — Young IG Auto Inspection System

This is a dedicated Pydantic Object Model that represents a fully assembled
inspection report, ready to be passed into the PDF generation layer.

It is NOT a database schema. It is a purpose-built data transfer object (DTO)
designed to make PDF generation trivial — just loop through the pre-grouped
'findings' and you have everything you need.

Usage:
    inspection = await repo.get_inspection_for_pdf(inspection_id)
    report = InspectionPDFReport.from_orm_object(inspection)
    # Pass `report` to your PDF generator (ReportLab, WeasyPrint, etc.)
"""

from pydantic import BaseModel, Field, field_validator
from typing import List, Optional, Dict
from uuid import UUID
from datetime import date, datetime

from src.enums import (
    InspectionStatus, OverallCondition,
    OdoMeasure, ImageCategory
)
from src.model import Inspection


# ─────────────────────────────────────────────────────────────────────────────
# NESTED COMPONENTS — Building blocks of the full report
# ─────────────────────────────────────────────────────────────────────────────

class PDFInspectorInfo(BaseModel):
    """Inspector who performed the inspection."""
    full_name: str
    email: str
    phone: Optional[str] = None

    model_config = {"from_attributes": True}


class PDFCustomerInfo(BaseModel):
    """Customer who brought the vehicle in."""
    full_name: str
    email: Optional[str] = None
    phone: Optional[str] = None
    kra_pin: Optional[str] = None

    model_config = {"from_attributes": True}


class PDFVehicleInfo(BaseModel):
    """Vehicle that was inspected."""
    registration_number: str
    make: Optional[str] = None
    model: Optional[str] = None
    manufacture_year: Optional[int] = None
    fuel_type: Optional[str] = None
    transmission: Optional[str] = None
    vehicle_type: Optional[str] = None
    engine_number: Optional[str] = None
    chassis_number: Optional[str] = None

    model_config = {"from_attributes": True}


class PDFFinding(BaseModel):
    """
    A single inspection result line — one field and the value recorded.
    The inspector may also have left notes on this specific item.
    """
    field_name: str
    value: Optional[str] = None
    notes: Optional[str] = None


class PDFCategoryFindings(BaseModel):
    """
    A named section (category) containing all its findings.
    E.g. 'Engine' -> [Oil Level: Good, Timing Belt: Worn, ...]
    This is the key grouping that makes the PDF easy to render section by section.
    """
    category_name: str
    display_order: Optional[int] = None
    findings: List[PDFFinding] = []


class PDFImage(BaseModel):
    """A single image linked to the inspection."""
    image_url: str
    image_category: Optional[ImageCategory] = None
    uploaded_at: Optional[datetime] = None

    model_config = {"from_attributes": True}


# ─────────────────────────────────────────────────────────────────────────────
# MAIN REPORT OBJECT — The complete, assembled PDF data model
# ─────────────────────────────────────────────────────────────────────────────

class InspectionPDFReport(BaseModel):
    """
    The complete, self-contained inspection report object.

    When populated via `from_orm_object()`, this model holds everything a PDF
    generator needs. No more database calls, no more lazy loading, no N+1 issues.

    Structure:
        report.inspection_info    -> Core inspection details
        report.vehicle_info       -> All vehicle details
        report.customer_info      -> Customer details (or None if walk-in)
        report.inspector_info     -> Inspector details
        report.findings_by_cat    -> List of categories, each with their findings
        report.images_by_category -> Images grouped by category (EXTERIOR, ENGINE, etc.)
        report.summary            -> Final recommendation, notes, mileage warning
    """

    # ── Inspection metadata ──────────────────────────────────────────────────
    inspection_id: UUID
    inspection_number: str
    inspection_date: date
    status: InspectionStatus
    created_at: Optional[datetime] = None

    # ── Parties involved ─────────────────────────────────────────────────────
    inspector_info: PDFInspectorInfo
    vehicle_info: PDFVehicleInfo
    customer_info: Optional[PDFCustomerInfo] = None
    seller_name: Optional[str] = None          # seller may differ from customer

    # ── Mileage ──────────────────────────────────────────────────────────────
    mileage: Optional[int] = None
    odo_measure: Optional[OdoMeasure] = None
    mileage_authentic: Optional[bool] = None   # False = TAMPERED flag on PDF

    # ── Findings grouped by category ─────────────────────────────────────────
    # This is the heart of the PDF — pre-grouped so the template just loops categories
    findings_by_category: List[PDFCategoryFindings] = []

    # ── Images grouped by category ───────────────────────────────────────────
    images_by_category: Dict[str, List[PDFImage]] = {}

    # ── Final summary ────────────────────────────────────────────────────────
    overall_condition: Optional[OverallCondition] = None
    final_notes: Optional[str] = None

    # ── Generated PDF storage URL (populated after generation) ───────────────
    pdf_url: Optional[str] = None

    @classmethod
    def from_orm_object(cls, inspection: Inspection) -> "InspectionPDFReport":
        """
        Factory method: converts a fully-loaded SQLAlchemy `Inspection` ORM object
        (as returned by `get_inspection_for_pdf()`) into this clean PDF report model.

        This method handles all the data transformation and grouping so the
        PDF generator only has to focus on rendering, not data logic.
        """
        # ── 1. Build category findings map ───────────────────────────────────
        # We collect findings into a dict keyed by category name first,
        # then sort by category display_order for consistent PDF layout.
        category_map: Dict[str, PDFCategoryFindings] = {}

        for result in (inspection.results or []):
            field = result.field
            category = field.category if field else None

            cat_name = category.name if category else "General"
            cat_order = category.display_order if category else 999

            if cat_name not in category_map:
                category_map[cat_name] = PDFCategoryFindings(
                    category_name=cat_name,
                    display_order=cat_order,
                    findings=[]
                )

            category_map[cat_name].findings.append(
                PDFFinding(
                    field_name=field.field_name if field else "Unknown",
                    value=result.filed_value,
                    notes=result.notes
                )
            )

        # Sort categories by display_order so the PDF sections are ordered correctly
        sorted_categories = sorted(
            category_map.values(),
            key=lambda c: (c.display_order or 999)
        )

        # ── 2. Build images by category map ──────────────────────────────────
        images_by_cat: Dict[str, List[PDFImage]] = {}
        for img in (inspection.images or []):
            cat_key = img.image_category.value if img.image_category else "OTHER"
            if cat_key not in images_by_cat:
                images_by_cat[cat_key] = []
            images_by_cat[cat_key].append(
                PDFImage(
                    image_url=img.image_url,
                    image_category=img.image_category,
                    uploaded_at=img.uploaded_at
                )
            )

        # ── 3. Build inspector / customer / vehicle sub-objects ───────────────
        inspector_info = PDFInspectorInfo(
            full_name=inspection.inspector.full_name,
            email=inspection.inspector.email,
            phone=inspection.inspector.phone
        )

        vehicle_info = PDFVehicleInfo(
            registration_number=inspection.vehicle.registration_number,
            make=inspection.vehicle.make,
            model=inspection.vehicle.model,
            manufacture_year=inspection.vehicle.manufacture_year,
            fuel_type=inspection.vehicle.fuel_type.value if inspection.vehicle.fuel_type else None,
            transmission=inspection.vehicle.transmission.value if inspection.vehicle.transmission else None,
            vehicle_type=inspection.vehicle.vehicle_type.value if inspection.vehicle.vehicle_type else None,
            engine_number=inspection.vehicle.engine_number,
            chassis_number=inspection.vehicle.chassis_number
        )

        customer_info = None
        if inspection.customer:
            customer_info = PDFCustomerInfo(
                full_name=inspection.customer.full_name,
                email=inspection.customer.email,
                phone=inspection.customer.phone,
                kra_pin=inspection.customer.kra_pin
            )

        # ── 4. Assemble and return the full report ────────────────────────────
        return cls(
            inspection_id=inspection.id,
            inspection_number=inspection.inspection_number,
            inspection_date=inspection.inspection_date,
            status=inspection.status,
            created_at=inspection.created_at,
            inspector_info=inspector_info,
            vehicle_info=vehicle_info,
            customer_info=customer_info,
            seller_name=inspection.seller_name,
            mileage=inspection.mileage,
            odo_measure=inspection.odo_measure,
            mileage_authentic=inspection.mileage_authentic,
            findings_by_category=sorted_categories,
            images_by_category=images_by_cat,
            overall_condition=inspection.overall_condition,
            final_notes=inspection.final_notes,
            pdf_url=inspection.pdf_url
        )
