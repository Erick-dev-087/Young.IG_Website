"""
Inspection Repository — Young IG Auto Inspection System

Covers all operational queries (day-to-day running), analytical queries (business insights),
and the critical PDF super-query that loads a complete inspection in a single database round-trip.
"""

from sqlalchemy import select, func, and_, desc, distinct, case, cast, Float
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload, joinedload
from uuid import UUID
from datetime import date, timedelta
from typing import List, Tuple, Optional, Dict, Any

from .base import BaseRepository
from src.model import (
    Inspection, InspectionResult, InspectionField,
    InspectionCategory, InspectionImage, Vehicle, Customer, User
)
from src.enums import InspectionStatus, OverallCondition


class InspectionRepository(BaseRepository[Inspection]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(Inspection, db_session)

    # ─────────────────────────────────────────────────────────────────────────
    # OPERATIONAL QUERIES — Day-to-day queries for inspectors and admin
    # ─────────────────────────────────────────────────────────────────────────

    async def get_by_number(self, inspection_number: str) -> Optional[Inspection]:
        """Look up a single inspection by its human-readable reference number."""
        query = select(Inspection).where(Inspection.inspection_number == inspection_number)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_status(
        self,
        status: InspectionStatus,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """Get all inspections filtered by status (e.g. DRAFT, IN_PROGRESS, COMPLETED)."""
        query = select(Inspection).where(Inspection.status == status).order_by(desc(Inspection.inspection_date))
        count_query = select(func.count(Inspection.id)).where(Inspection.status == status)

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_pending_by_inspector(self, inspector_id: UUID) -> List[Inspection]:
        """
        Get all open (DRAFT / IN_PROGRESS) inspections for a specific inspector.
        This is the inspector's personal work queue shown on their dashboard.
        """
        query = (
            select(Inspection)
            .where(
                and_(
                    Inspection.inspector_id == inspector_id,
                    Inspection.status.in_([InspectionStatus.DRAFT, InspectionStatus.IN_PROGRESS])
                )
            )
            .order_by(desc(Inspection.inspection_date))
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_inspector(
        self,
        inspector_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """Get all inspections ever done by a specific inspector, newest first."""
        query = (
            select(Inspection)
            .where(Inspection.inspector_id == inspector_id)
            .order_by(desc(Inspection.inspection_date))
        )
        count_query = select(func.count(Inspection.id)).where(Inspection.inspector_id == inspector_id)

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_by_vehicle(self, vehicle_id: UUID) -> List[Inspection]:
        """
        Get every inspection ever performed on a specific vehicle, newest first.
        This is the key method for pulling a car's full history.
        """
        query = (
            select(Inspection)
            .where(Inspection.vehicle_id == vehicle_id)
            .order_by(desc(Inspection.inspection_date))
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_customer(
        self,
        customer_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """Get all inspections tied to a specific customer."""
        query = (
            select(Inspection)
            .where(Inspection.customer_id == customer_id)
            .order_by(desc(Inspection.inspection_date))
        )
        count_query = select(func.count(Inspection.id)).where(Inspection.customer_id == customer_id)

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def search_by_vehicle_identifier(self, search_term: str) -> List[Inspection]:
        """
        Search inspections by registration number or chassis number.
        Useful when a customer calls in and you need to pull up their inspection quickly.
        """
        query = (
            select(Inspection)
            .join(Vehicle, Vehicle.id == Inspection.vehicle_id)
            .where(
                Vehicle.registration_number.ilike(f"%{search_term}%") |
                Vehicle.chassis_number.ilike(f"%{search_term}%")
            )
            .order_by(desc(Inspection.inspection_date))
        )
        result = await self.db_session.execute(query)
        return list(result.scalars().all())

    async def get_by_timeframe(
        self,
        start_date: date,
        end_date: date,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """Get inspections within any custom date range."""
        query = (
            select(Inspection)
            .where(
                and_(
                    Inspection.inspection_date >= start_date,
                    Inspection.inspection_date <= end_date
                )
            )
            .order_by(desc(Inspection.inspection_date))
        )
        count_query = select(func.count(Inspection.id)).where(
            and_(
                Inspection.inspection_date >= start_date,
                Inspection.inspection_date <= end_date
            )
        )

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_tampered_mileage_inspections(
        self,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """
        Retrieve all inspections where the odometer was marked as NOT authentic.
        Critical for fraud tracking and reporting to clients.
        """
        query = (
            select(Inspection)
            .where(Inspection.mileage_authentic == False)  # noqa: E712
            .order_by(desc(Inspection.inspection_date))
        )
        count_query = select(func.count(Inspection.id)).where(Inspection.mileage_authentic == False)  # noqa: E712

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_by_overall_condition(
        self,
        overall_condition: OverallCondition,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """
        Filter inspections by overall condition.
        Use OverallCondition.NO_MAJOR_ISSUES for clean cars,
        OverallCondition.CRITICAL_SAFETY_ISSUES for severely problematic ones.
        """
        query = (
            select(Inspection)
            .where(Inspection.overall_condition == overall_condition)
            .order_by(desc(Inspection.inspection_date))
        )
        count_query = select(func.count(Inspection.id)).where(Inspection.overall_condition == overall_condition)

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    async def get_with_specific_fault(
        self,
        field_name: str,
        fault_value: str,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Inspection], int]:
        """
        Find all inspections where a specific field recorded a specific value (the fault).
        E.g. field_name="Engine Health", fault_value="Poor"
        """
        query = (
            select(Inspection)
            .join(InspectionResult, InspectionResult.inspection_id == Inspection.id)
            .join(InspectionField, InspectionField.id == InspectionResult.inspection_field_id)
            .where(
                and_(
                    InspectionField.field_name.ilike(f"%{field_name}%"),
                    InspectionResult.filed_value.ilike(f"%{fault_value}%")
                )
            )
            .distinct()
            .order_by(desc(Inspection.inspection_date))
        )
        count_query = (
            select(func.count(distinct(Inspection.id)))
            .join(InspectionResult, InspectionResult.inspection_id == Inspection.id)
            .join(InspectionField, InspectionField.id == InspectionResult.inspection_field_id)
            .where(
                and_(
                    InspectionField.field_name.ilike(f"%{field_name}%"),
                    InspectionResult.filed_value.ilike(f"%{fault_value}%")
                )
            )
        )

        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0

    # ─────────────────────────────────────────────────────────────────────────
    # ANALYTICAL QUERIES — Business intelligence and dashboard metrics
    # ─────────────────────────────────────────────────────────────────────────

    async def get_performance_dashboard(self) -> Dict[str, Any]:
        """
        Single call that returns all the top-level stats for the admin dashboard.
        Covers today, this week, and this month to give a live pulse of the business.
        """
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)

        # Total all-time inspections
        total = await self.db_session.scalar(select(func.count(Inspection.id)))

        # Today
        today_count = await self.db_session.scalar(
            select(func.count(Inspection.id)).where(Inspection.inspection_date == today)
        )

        # This week
        week_count = await self.db_session.scalar(
            select(func.count(Inspection.id)).where(Inspection.inspection_date >= start_of_week)
        )

        # This month
        month_count = await self.db_session.scalar(
            select(func.count(Inspection.id)).where(Inspection.inspection_date >= start_of_month)
        )

        # Completed inspections this month
        completed_month = await self.db_session.scalar(
            select(func.count(Inspection.id)).where(
                and_(
                    Inspection.inspection_date >= start_of_month,
                    Inspection.status == InspectionStatus.COMPLETED
                )
            )
        )

        # Tampered odometer cases this month
        tampered_month = await self.db_session.scalar(
            select(func.count(Inspection.id)).where(
                and_(
                    Inspection.inspection_date >= start_of_month,
                    Inspection.mileage_authentic == False  # noqa: E712
                )
            )
        )

        return {
            "total_inspections_all_time": total or 0,
            "inspections_today": today_count or 0,
            "inspections_this_week": week_count or 0,
            "inspections_this_month": month_count or 0,
            "completed_this_month": completed_month or 0,
            "tampered_odometer_this_month": tampered_month or 0,
        }

    async def get_overall_condition_distribution(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, int]:
        """
        Get the count of each overall condition outcome.
        Answers: 'Of all cars inspected this month, how many had critical safety issues?'
        """
        query = (
            select(Inspection.overall_condition, func.count(Inspection.id))
            .where(Inspection.status == InspectionStatus.COMPLETED)
            .where(Inspection.overall_condition.isnot(None))
        )

        if start_date:
            query = query.where(Inspection.inspection_date >= start_date)
        if end_date:
            query = query.where(Inspection.inspection_date <= end_date)

        query = query.group_by(Inspection.overall_condition)
        result = await self.db_session.execute(query)

        return {
            rec.name if hasattr(rec, 'name') else str(rec): count
            for rec, count in result.all()
        }

    async def get_issue_severity_ratio(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, Any]:
        """
        High-level issue severity ratio.
        Returns counts and percentage for the frontend to render a pie chart.
        """
        dist = await self.get_overall_condition_distribution(start_date, end_date)

        clean = dist.get("NO_MAJOR_ISSUES", 0) + dist.get("MINOR_ISSUES_FOUND", 0)
        problematic = dist.get("MAJOR_ISSUES_FOUND", 0) + dist.get("CRITICAL_SAFETY_ISSUES", 0)
        total = clean + problematic

        return {
            "clean_or_minor_issues": clean,
            "major_or_critical_issues": problematic,
            "total": total,
            "clean_rate_pct": round((clean / total * 100), 1) if total > 0 else 0.0,
            "problematic_rate_pct": round((problematic / total * 100), 1) if total > 0 else 0.0,
        }

    async def get_most_common_faults(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Rank the most frequently occurring fault values across all completed inspections.
        Answers: 'What are the top 10 things wrong with cars we inspect?'
        This feeds the analytics dashboard chart and can inform business decisions.
        """
        query = (
            select(
                InspectionField.field_name,
                InspectionField.category_id,
                InspectionResult.filed_value,
                func.count(InspectionResult.id).label("occurrence_count")
            )
            .join(InspectionField, InspectionField.id == InspectionResult.inspection_field_id)
            .join(Inspection, Inspection.id == InspectionResult.inspection_id)
            .where(Inspection.status == InspectionStatus.COMPLETED)
            .where(InspectionResult.filed_value.isnot(None))
            .where(InspectionResult.filed_value != "")
        )

        if start_date:
            query = query.where(Inspection.inspection_date >= start_date)
        if end_date:
            query = query.where(Inspection.inspection_date <= end_date)

        query = (
            query.group_by(InspectionField.field_name, InspectionField.category_id, InspectionResult.filed_value)
            .order_by(desc("occurrence_count"))
            .limit(limit)
        )

        result = await self.db_session.execute(query)

        return [
            {
                "field_name": row.field_name,
                "fault_value": row.filed_value,
                "occurrences": row.occurrence_count
            }
            for row in result.all()
        ]

    async def get_daily_inspection_trend(
        self,
        start_date: date,
        end_date: date
    ) -> List[Dict[str, Any]]:
        """
        Returns daily inspection counts between two dates.
        Used to render a line/bar chart on the analytics dashboard showing business volume over time.
        """
        query = (
            select(
                Inspection.inspection_date,
                func.count(Inspection.id).label("count")
            )
            .where(
                and_(
                    Inspection.inspection_date >= start_date,
                    Inspection.inspection_date <= end_date
                )
            )
            .group_by(Inspection.inspection_date)
            .order_by(Inspection.inspection_date)
        )

        result = await self.db_session.execute(query)

        return [
            {"date": str(row.inspection_date), "count": row.count}
            for row in result.all()
        ]

    async def get_status_breakdown(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None
    ) -> Dict[str, int]:
        """
        Count inspections grouped by status for a given period.
        Useful for seeing how many are stuck in DRAFT vs COMPLETED.
        """
        query = select(Inspection.status, func.count(Inspection.id))

        if start_date:
            query = query.where(Inspection.inspection_date >= start_date)
        if end_date:
            query = query.where(Inspection.inspection_date <= end_date)

        query = query.group_by(Inspection.status)
        result = await self.db_session.execute(query)

        return {
            status.name if hasattr(status, 'name') else str(status): count
            for status, count in result.all()
        }

    # ─────────────────────────────────────────────────────────────────────────
    # PDF SUPER-QUERY — Single round-trip to load everything for PDF generation
    # ─────────────────────────────────────────────────────────────────────────

    async def get_inspection_for_pdf(self, inspection_id: UUID) -> Optional[Inspection]:
        """
        Fetches a complete inspection in ONE database round-trip, eagerly loading
        every related object the PDF needs:
            - Inspector (User) details
            - Customer details
            - Vehicle details
            - All InspectionResults, with each result's InspectionField
              and the field's InspectionCategory (so we can group by category)
            - All InspectionImages (with category labels)

        After calling this, zero additional DB queries are needed to generate the PDF.
        Simply pass the returned object to the InspectionPDFReport Pydantic model.
        """
        query = (
            select(Inspection)
            .where(Inspection.id == inspection_id)
            .options(
                # Load inspector's user record
                joinedload(Inspection.inspector),
                # Load customer record
                joinedload(Inspection.customer),
                # Load vehicle record
                joinedload(Inspection.vehicle),
                # Load all results, then for each result load its field,
                # and for each field load its category
                selectinload(Inspection.results)
                    .joinedload(InspectionResult.field)
                    .joinedload(InspectionField.category),
                # Load all images
                selectinload(Inspection.images),
            )
        )

        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()