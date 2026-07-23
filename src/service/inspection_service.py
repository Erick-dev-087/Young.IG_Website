"""
Inspection Service — Young IG Auto Inspection System

Core business logic for the inspection lifecycle:
  - CRUD (create, read, update, delete / cancel)
  - Status transitions (DRAFT → IN_PROGRESS → COMPLETED → ARCHIVED)
  - Submitting inspection results (the form data filled by inspectors)
  - Search and filtering (by status, condition, vehicle, customer, timeframe, fault)
  - Analytics and productivity metrics
  - PDF report assembly trigger
"""

from uuid import UUID
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..model import Inspection, InspectionResult
from ..repositories.inspections_repository import InspectionRepository
from ..repositories.user_repository import UserRepository
from ..repositories.vehicle_repository import VehicleRepository
from ..Schemas.inspection import InspectionCreate, InspectionUpdate
from ..Schemas.inspection_result import InspectionResultCreate, InspectionResultUpdate
from ..schemas.inspection_pdf_report import InspectionPDFReport
from ..enums import (
    InspectionStatus, OverallCondition, UserStatus, UserRole
)


# ---------------------------------------------------------------------------
# Helper: valid status transitions
# ---------------------------------------------------------------------------

_VALID_TRANSITIONS: Dict[InspectionStatus, List[InspectionStatus]] = {
    InspectionStatus.DRAFT:       [InspectionStatus.IN_PROGRESS, InspectionStatus.ARCHIVED],
    InspectionStatus.IN_PROGRESS: [InspectionStatus.COMPLETED, InspectionStatus.DRAFT, InspectionStatus.ARCHIVED],
    InspectionStatus.COMPLETED:   [InspectionStatus.ARCHIVED],
    InspectionStatus.ARCHIVED:    [],  # terminal
}


class InspectionService:
    """
    Orchestrates the full inspection lifecycle from creation through to
    PDF generation. Coordinates between InspectionRepository,
    UserRepository, and VehicleRepository.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.repo = InspectionRepository(db)
        self.user_repo = UserRepository(db)
        self.vehicle_repo = VehicleRepository(db)

    # -------------------------------------------------------------------------
    # CRUD — Core operations
    # -------------------------------------------------------------------------

    async def create(self, data: InspectionCreate) -> Inspection:
        """
        Create a new inspection in DRAFT status.

        Validates:
          - The inspector exists and is an approved inspector
          - The vehicle exists
          - No duplicate inspection number
        """
        # 1. Validate inspector
        inspector = await self.user_repo.get_by_id(data.inspector_id)
        if not inspector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspector not found.",
            )
        if inspector.status != UserStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Inspector account is not approved.",
            )
        if inspector.role != UserRole.INSPECTOR:
            raise HTTPException(
                status_code=status.HTTP_403_FORBIDDEN,
                detail="Assigned user is not an inspector.",
            )

        # 2. Validate vehicle exists
        vehicle = await self.vehicle_repo.get_by_id(data.vehicle_id)
        if not vehicle:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Vehicle not found. Register the vehicle first.",
            )

        # 3. Check for duplicate inspection number
        existing = await self.repo.get_by_number(data.inspection_number)
        if existing:
            raise HTTPException(
                status_code=status.HTTP_409_CONFLICT,
                detail=f"Inspection number '{data.inspection_number}' is already in use.",
            )

        # 4. Create with DRAFT status (status is set by model default)
        inspection_data = data.model_dump()
        inspection = await self.repo.create(**inspection_data)

        logger.info(
            f"Inspection created: {inspection.inspection_number} "
            f"(vehicle={vehicle.registration_number}, inspector={inspector.full_name})"
        )
        return inspection

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        """Paginated list of all inspections."""
        return await self.repo.get_all(skip=skip, limit=limit)

    async def get_by_id(self, inspection_id: UUID) -> Inspection:
        """Fetch a single inspection or raise 404."""
        inspection = await self.repo.get_by_id(inspection_id)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found.",
            )
        return inspection

    async def get_by_number(self, inspection_number: str) -> Inspection:
        """Fetch an inspection by its human-readable reference number."""
        inspection = await self.repo.get_by_number(inspection_number)
        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail=f"Inspection '{inspection_number}' not found.",
            )
        return inspection

    async def update(
        self,
        inspection_id: UUID,
        data: InspectionUpdate,
        requesting_user_id: UUID,
    ) -> Inspection:
        """
        Update an inspection's details.

        Business rules:
          - COMPLETED or ARCHIVED inspections cannot be freely edited.
            Only admin-level status changes are permitted (handled by
            `transition_status`).
          - If `status` is included in the update, we delegate to
            `transition_status` to enforce the valid transition rules.
        """
        inspection = await self.get_by_id(inspection_id)

        if inspection.status in (InspectionStatus.COMPLETED, InspectionStatus.ARCHIVED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot edit a '{inspection.status.value}' inspection.",
            )

        update_data = data.model_dump(exclude_unset=True)

        # If status change requested, route through the proper transition method
        if "status" in update_data:
            new_status = update_data.pop("status")
            inspection = await self.transition_status(inspection_id, new_status, requesting_user_id)

        if update_data:
            updated = await self.repo.update(inspection_id, **update_data)
            if not updated:
                raise HTTPException(
                    status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Failed to update inspection.",
                )
            inspection = updated

        logger.info(f"Inspection updated: {inspection.inspection_number}")
        return inspection

    async def delete(self, inspection_id: UUID) -> Dict[str, str]:
        """
        Hard-deletes an inspection. Should only be allowed for DRAFT inspections.
        Completed inspections should be ARCHIVED instead.
        """
        inspection = await self.get_by_id(inspection_id)

        if inspection.status != InspectionStatus.DRAFT:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Only DRAFT inspections can be deleted. "
                    f"This inspection is '{inspection.status.value}'. "
                    f"Archive it instead."
                ),
            )

        await self.repo.hard_delete(inspection_id)
        logger.info(f"Inspection deleted: {inspection.inspection_number}")
        return {"message": f"Inspection '{inspection.inspection_number}' has been deleted."}

    # -------------------------------------------------------------------------
    # STATUS TRANSITIONS — Controlled lifecycle management
    # -------------------------------------------------------------------------

    async def transition_status(
        self,
        inspection_id: UUID,
        new_status: InspectionStatus,
        requesting_user_id: UUID,
    ) -> Inspection:
        """
        Move an inspection through its lifecycle. Enforces valid transitions:
          DRAFT → IN_PROGRESS → COMPLETED → ARCHIVED

        Completing an inspection requires a final_notes or overall_condition.
        """
        inspection = await self.get_by_id(inspection_id)
        current_status = inspection.status

        allowed = _VALID_TRANSITIONS.get(current_status, [])
        if new_status not in allowed:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"Cannot transition from '{current_status.value}' to '{new_status.value}'. "
                    f"Allowed transitions: {[s.value for s in allowed] or 'none (terminal state)'}."
                ),
            )

        # Extra guard: completing an inspection requires a condition to be set
        if new_status == InspectionStatus.COMPLETED:
            if not inspection.overall_condition and not inspection.final_notes:
                raise HTTPException(
                    status_code=status.HTTP_400_BAD_REQUEST,
                    detail=(
                        "Cannot complete an inspection without setting an overall condition "
                        "or final notes. Fill these in before marking as complete."
                    ),
                )

        updated = await self.repo.update(inspection_id, status=new_status)
        logger.info(
            f"Inspection {inspection.inspection_number} status: "
            f"{current_status.value} → {new_status.value} (by user {requesting_user_id})"
        )
        return updated

    async def start_inspection(self, inspection_id: UUID, inspector_id: UUID) -> Inspection:
        """Shortcut: DRAFT → IN_PROGRESS."""
        return await self.transition_status(inspection_id, InspectionStatus.IN_PROGRESS, inspector_id)

    async def complete_inspection(
        self,
        inspection_id: UUID,
        inspector_id: UUID,
        overall_condition: OverallCondition,
        final_notes: Optional[str] = None,
    ) -> Inspection:
        """
        Shortcut: IN_PROGRESS → COMPLETED.
        Sets overall_condition and optional final_notes in one call,
        then triggers the status transition.
        """
        inspection = await self.get_by_id(inspection_id)

        # Set the condition before transitioning so the guard passes
        await self.repo.update(
            inspection_id,
            overall_condition=overall_condition,
            final_notes=final_notes,
        )

        return await self.transition_status(inspection_id, InspectionStatus.COMPLETED, inspector_id)

    async def archive_inspection(self, inspection_id: UUID, admin_id: UUID) -> Inspection:
        """Shortcut: COMPLETED → ARCHIVED."""
        return await self.transition_status(inspection_id, InspectionStatus.ARCHIVED, admin_id)

    # -------------------------------------------------------------------------
    # RESULTS — The actual form data filled by the inspector
    # -------------------------------------------------------------------------

    async def submit_result(
        self,
        inspection_id: UUID,
        result_data: InspectionResultCreate,
    ) -> InspectionResult:
        """
        Submit or update a single field result on an inspection.
        If a result already exists for that field, it is overwritten.
        Only allowed on DRAFT or IN_PROGRESS inspections.
        """
        inspection = await self.get_by_id(inspection_id)

        if inspection.status not in (InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add results to a '{inspection.status.value}' inspection.",
            )

        # Check if a result for this field already exists on this inspection
        from sqlalchemy import select
        from ..model import InspectionResult as InspectionResultModel

        existing_query = (
            select(InspectionResultModel)
            .where(
                InspectionResultModel.inspection_id == inspection_id,
                InspectionResultModel.inspection_field_id == result_data.inspection_field_id,
            )
        )
        existing_result = await self.db.execute(existing_query)
        existing = existing_result.scalar_one_or_none()

        if existing:
            # Update the existing result
            existing.filed_value = result_data.filed_value
            existing.notes = result_data.notes
            await self.db.flush()
            await self.db.refresh(existing)
            return existing
        else:
            # Create a new result
            new_result = InspectionResultModel(
                inspection_id=inspection_id,
                inspection_field_id=result_data.inspection_field_id,
                filed_value=result_data.filed_value,
                notes=result_data.notes,
            )
            self.db.add(new_result)
            await self.db.flush()
            await self.db.refresh(new_result)
            return new_result

    async def submit_bulk_results(
        self,
        inspection_id: UUID,
        results: List[InspectionResultCreate],
    ) -> Dict[str, Any]:
        """
        Submit multiple field results at once — the standard flow when
        an inspector saves an entire form page.
        """
        inspection = await self.get_by_id(inspection_id)

        if inspection.status not in (InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot add results to a '{inspection.status.value}' inspection.",
            )

        saved_count = 0
        for result_data in results:
            await self.submit_result(inspection_id, result_data)
            saved_count += 1

        logger.info(f"Bulk results submitted: {saved_count} fields for inspection {inspection_id}")
        return {
            "inspection_id": str(inspection_id),
            "results_saved": saved_count,
            "message": f"{saved_count} result(s) saved successfully.",
        }

    # -------------------------------------------------------------------------
    # SEARCH & FILTERING — Operational queries
    # -------------------------------------------------------------------------

    async def get_by_status(
        self,
        inspection_status: InspectionStatus,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        return await self.repo.get_by_status(inspection_status, skip=skip, limit=limit)

    async def get_by_overall_condition(
        self,
        condition: OverallCondition,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        return await self.repo.get_by_overall_condition(condition, skip=skip, limit=limit)

    async def get_by_inspector(
        self,
        inspector_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        return await self.repo.get_by_inspector(inspector_id, skip=skip, limit=limit)

    async def get_inspector_queue(self, inspector_id: UUID) -> List[Inspection]:
        """
        Returns an inspector's open work queue: all DRAFT and IN_PROGRESS
        inspections assigned to them. This is what an inspector sees on login.
        """
        return await self.repo.get_pending_by_inspector(inspector_id)

    async def get_by_vehicle(self, vehicle_id: UUID) -> List[Inspection]:
        return await self.repo.get_by_vehicle(vehicle_id)

    async def get_by_customer(
        self,
        customer_id: UUID,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        return await self.repo.get_by_customer(customer_id, skip=skip, limit=limit)

    async def get_by_timeframe(
        self,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date.",
            )
        return await self.repo.get_by_timeframe(start_date, end_date, skip=skip, limit=limit)

    async def search_by_vehicle_identifier(self, search_term: str) -> List[Inspection]:
        """
        Search by reg number or chassis number.
        Blank search term raises 400 rather than querying everything.
        """
        if not search_term or not search_term.strip():
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="Search term cannot be empty.",
            )
        return await self.repo.search_by_vehicle_identifier(search_term.strip())

    async def get_tampered_mileage_cases(
        self,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        """All inspections where odometer was marked as tampered/unauthentic."""
        return await self.repo.get_tampered_mileage_inspections(skip=skip, limit=limit)

    async def find_by_fault(
        self,
        field_name: str,
        fault_value: str,
        skip: int = 0,
        limit: int = 100,
    ) -> Tuple[List[Inspection], int]:
        """Find inspections where a specific field has a specific value."""
        return await self.repo.get_with_specific_fault(field_name, fault_value, skip=skip, limit=limit)

    # -------------------------------------------------------------------------
    # ANALYTICS — Dashboard and business intelligence
    # -------------------------------------------------------------------------

    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Master dashboard call: volumes today, this week, this month,
        completion rate, and tampered odometer count this month.
        """
        return await self.repo.get_performance_dashboard()

    async def get_status_breakdown(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, int]:
        """
        Count inspections grouped by status for a given period.
        Tells admin: how many are stuck in DRAFT vs completed this month.
        """
        return await self.repo.get_status_breakdown(start_date, end_date)

    async def get_condition_distribution(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, int]:
        """
        Breakdown of overall condition outcomes across completed inspections.
        Feeds the pie chart on the analytics dashboard.
        """
        return await self.repo.get_overall_condition_distribution(start_date, end_date)

    async def get_severity_ratio(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Clean vs problematic car ratio with percentages.
        """
        return await self.repo.get_issue_severity_ratio(start_date, end_date)

    async def get_most_common_faults(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Top N most frequently reported faults across all completed inspections.
        """
        return await self.repo.get_most_common_faults(start_date, end_date, limit=limit)

    async def get_daily_trend(
        self,
        start_date: date,
        end_date: date,
    ) -> List[Dict[str, Any]]:
        """
        Day-by-day inspection volume for line/bar charts.
        """
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date.",
            )
        return await self.repo.get_daily_inspection_trend(start_date, end_date)

    # -------------------------------------------------------------------------
    # PDF ASSEMBLY — Loads the full inspection object for PDF generation
    # -------------------------------------------------------------------------

    async def build_pdf_report(self, inspection_id: UUID) -> InspectionPDFReport:
        """
        Fetches the inspection with ALL relationships in one query and assembles
        the InspectionPDFReport DTO. The PDF generator receives this and needs
        no further database calls.
        """
        inspection = await self.repo.get_inspection_for_pdf(inspection_id)

        if not inspection:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspection not found.",
            )

        if inspection.status not in (InspectionStatus.IN_PROGRESS, InspectionStatus.COMPLETED):
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=(
                    f"PDF can only be generated for IN_PROGRESS or COMPLETED inspections. "
                    f"Current status: '{inspection.status.value}'."
                ),
            )

        report = InspectionPDFReport.from_orm_object(inspection)
        logger.info(f"PDF report assembled for inspection: {inspection.inspection_number}")
        return report

    async def store_pdf_url(self, inspection_id: UUID, pdf_url: str) -> Inspection:
        """
        After the PDF is generated and uploaded to storage, store its URL
        back on the inspection record so it can be retrieved later.
        """
        inspection = await self.get_by_id(inspection_id)
        updated = await self.repo.update(inspection_id, pdf_url=pdf_url)
        logger.info(f"PDF URL stored for inspection: {inspection.inspection_number}")
        return updated
