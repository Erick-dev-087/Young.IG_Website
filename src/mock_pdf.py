import sys
import os
from uuid import uuid4
from datetime import date, datetime

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from src.schemas.inspection_pdf_report import (
    InspectionPDFReport, PDFInspectorInfo, PDFCustomerInfo,
    PDFVehicleInfo, PDFCategoryFindings, PDFFinding, PDFImage
)
from src.enums import InspectionStatus, OverallCondition, OdoMeasure, ImageCategory
from src.service.pdf_service import _render_html


report = InspectionPDFReport(
    inspection_id=uuid4(),
    inspection_number="YIG-2026-001",
    inspection_date=date.today(),
    status=InspectionStatus.COMPLETED,
    created_at=datetime.now(),
    inspector_info=PDFInspectorInfo(
        full_name="Ian Wahome",
        email="ian@youngig.com",
        phone="+254 700 000 000"
    ),
    vehicle_info=PDFVehicleInfo(
        registration_number="KCA 505S",
        make="Mercedes Benz",
        model="C180 Kompressor",
        manufacture_year=2008,
        fuel_type="Petrol",
        transmission="Automatic",
        vehicle_type="Internal Combustion",
        engine_number="27195231006432",
        chassis_number="WDD2040462A103328"
    ),
    customer_info=PDFCustomerInfo(
        full_name="John Kamau",
        email="jkamau@email.com",
        phone="+254 711 111 111",
        kra_pin="A123456789Z"
    ),
    seller_name="Galleria Motors",
    mileage=191056,
    odo_measure=OdoMeasure.KMS,
    mileage_authentic=True,
    overall_condition=OverallCondition.MINOR_ISSUES_FOUND,
    final_notes=(
        "The vehicle is generally in good mechanical health for its age and mileage. "
        "The engine starts smoothly and has no unusual noises. However, the coolant level "
        "is low and should be topped up. Minor surface scratches on the rear bumper were "
        "observed — cosmetic only and do not affect roadworthiness."
    ),
    findings_by_category=[
        PDFCategoryFindings(
            category_name="Engine",
            display_order=1,
            findings=[
                PDFFinding(field_name="Engine Oil Level", value="Good"),
                PDFFinding(field_name="Engine Noise", value="Normal"),
                PDFFinding(field_name="Coolant Level", value="Low", notes="Needs topping up soon."),
                PDFFinding(field_name="Timing Belt Condition", value="Worn", notes="Approaching service interval."),
                PDFFinding(field_name="Turbo / Supercharger", value="N/A"),
                PDFFinding(field_name="Oil Leaks", value="None"),
            ]
        ),
        PDFCategoryFindings(
            category_name="Exterior",
            display_order=2,
            findings=[
                PDFFinding(field_name="Paint Condition", value="Good"),
                PDFFinding(field_name="Dents & Scratches", value="Minor scratches on rear bumper"),
                PDFFinding(field_name="Windscreen", value="Good"),
                PDFFinding(field_name="All Lights Functional", value="Good"),
                PDFFinding(field_name="Tyres — Front", value="Good"),
                PDFFinding(field_name="Tyres — Rear", value="Worn", notes="Replace within 5,000 km."),
            ]
        ),
        PDFCategoryFindings(
            category_name="Interior",
            display_order=3,
            findings=[
                PDFFinding(field_name="Dashboard Lights", value="Good"),
                PDFFinding(field_name="Air Conditioning", value="Good"),
                PDFFinding(field_name="Seats & Upholstery", value="Good"),
                PDFFinding(field_name="Infotainment / Radio", value="Damaged", notes="Display cracked."),
                PDFFinding(field_name="Seatbelts", value="Good"),
            ]
        ),
        PDFCategoryFindings(
            category_name="Undercarriage",
            display_order=4,
            findings=[
                PDFFinding(field_name="Chassis Integrity", value="Good"),
                PDFFinding(field_name="Exhaust System", value="Good"),
                PDFFinding(field_name="Brake Lines", value="Good"),
                PDFFinding(field_name="Suspension — Front", value="Good"),
                PDFFinding(field_name="Suspension — Rear", value="Worn", notes="Shock absorbers showing wear."),
            ]
        ),
    ],
    images_by_category={
        "EXTERIOR": [
            PDFImage(image_url="https://via.placeholder.com/400x300/1e293b/ffffff?text=Front+View", image_category=ImageCategory.EXTERIOR),
            PDFImage(image_url="https://via.placeholder.com/400x300/1e293b/ffffff?text=Rear+View", image_category=ImageCategory.EXTERIOR),
            PDFImage(image_url="https://via.placeholder.com/400x300/334155/ffffff?text=Side+Profile", image_category=ImageCategory.EXTERIOR),
        ],
        "ENGINE": [
            PDFImage(image_url="https://via.placeholder.com/400x300/0f172a/ffffff?text=Engine+Bay", image_category=ImageCategory.ENGINE),
        ],
        "INTERIOR": [
            PDFImage(image_url="https://via.placeholder.com/400x300/475569/ffffff?text=Dashboard", image_category=ImageCategory.INTERIOR),
            PDFImage(image_url="https://via.placeholder.com/400x300/64748b/ffffff?text=Rear+Seats", image_category=ImageCategory.INTERIOR),
        ],
    }
)

html_content = _render_html(report)
filepath = os.path.join(os.path.dirname(os.path.abspath(__file__)), "assets", "mock_report.html")
os.makedirs(os.path.dirname(filepath), exist_ok=True)
with open(filepath, "w", encoding="utf-8") as f:
    f.write(html_content)
print(f"Mock HTML preview generated: {filepath}")
