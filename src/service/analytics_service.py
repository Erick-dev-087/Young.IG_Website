"""
Analytics Service — Young IG Auto Inspection System

A unified service that aggregates metrics from inspections, customers,
vehicles, and inspectors into the views the admin dashboard actually needs.

Rather than having the frontend call four separate endpoints and stitch
them together, this service exposes single calls that return fully composed
dashboard payloads — fast and with minimal database round-trips.
"""

from datetime import date, timedelta
from typing import Dict, Any, List, Optional
from uuid import UUID

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..repositories.inspections_repository import InspectionRepository
from ..repositories.customer_repository import CustomerRepository
from ..repositories.vehicle_repository import VehicleRepository
from ..repositories.user_repository import UserRepository
from ..enums import UserRole


class AnalyticsService:
    """
    Composes cross-entity analytics for admin dashboards and reports.
    All methods are read-only — no mutations happen here.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.inspection_repo = InspectionRepository(db)
        self.customer_repo = CustomerRepository(db)
        self.vehicle_repo = VehicleRepository(db)
        self.user_repo = UserRepository(db)

    # -------------------------------------------------------------------------
    # MASTER DASHBOARD — Single call for the admin home screen
    # -------------------------------------------------------------------------

    async def get_admin_dashboard(self) -> Dict[str, Any]:
        """
        One call to power the entire admin dashboard home screen.

        Returns:
          - inspection_volume: today, week, month, all-time, completion rate
          - customer_activity: total customers, served today/week/month
          - inspector_health: total inspectors, pending approvals
          - fraud_alerts: tampered odometer count this month
          - condition_snapshot: distribution of overall conditions this month
        """
        today = date.today()
        start_of_month = today.replace(day=1)

        # ── 1. Inspection volume ────────────────────────────────────────────
        inspection_dash = await self.inspection_repo.get_performance_dashboard()

        # ── 2. Customer activity ────────────────────────────────────────────
        customer_dash = await self.customer_repo.get_performance_dashboard()

        # ── 3. Inspector health ─────────────────────────────────────────────
        _, total_inspectors = await self.user_repo.get_by_role(UserRole.INSPECTOR, limit=1)
        _, pending_approvals = await self.user_repo.get_by_status(
            # Import here to avoid circular imports
            __import__("src.enums", fromlist=["UserStatus"]).UserStatus.PENDING,
            limit=1
        )

        # ── 4. Condition snapshot for this month ────────────────────────────
        condition_dist = await self.inspection_repo.get_overall_condition_distribution(
            start_date=start_of_month
        )

        # ── 5. Severity ratio for this month ────────────────────────────────
        severity = await self.inspection_repo.get_issue_severity_ratio(
            start_date=start_of_month
        )

        return {
            "as_of": str(today),
            "inspection_volume": {
                "all_time": inspection_dash["total_inspections_all_time"],
                "today": inspection_dash["inspections_today"],
                "this_week": inspection_dash["inspections_this_week"],
                "this_month": inspection_dash["inspections_this_month"],
                "completed_this_month": inspection_dash["completed_this_month"],
            },
            "customer_activity": {
                "total_in_system": customer_dash["total_customers_in_system"],
                "served_today": customer_dash["customers_served_today"],
                "served_this_week": customer_dash["customers_served_this_week"],
                "served_this_month": customer_dash["customers_served_this_month"],
            },
            "inspector_health": {
                "total_inspectors": total_inspectors,
                "pending_approvals": pending_approvals,
            },
            "fraud_alerts": {
                "tampered_odometers_this_month": inspection_dash["tampered_odometer_this_month"],
            },
            "condition_snapshot_this_month": condition_dist,
            "severity_ratio_this_month": severity,
        }

    # -------------------------------------------------------------------------
    # INSPECTOR REPORT — Everything about one inspector's performance
    # -------------------------------------------------------------------------

    async def get_inspector_report(
        self,
        inspector_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Comprehensive productivity report for a single inspector.
        Used in the admin "inspector detail" view and for weekly reports.
        """
        inspector = await self.user_repo.get_by_id(inspector_id)
        if not inspector:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Inspector not found.",
            )

        total = await self.user_repo.get_inspector_inspection_count(
            inspector_id, start_date, end_date
        )
        status_breakdown = await self.user_repo.get_inspector_status_breakdown(
            inspector_id, start_date, end_date
        )

        # Customers this inspector served in the period
        _, customers_served = await self.customer_repo.get_by_inspector(inspector_id, limit=1)

        return {
            "inspector_id": str(inspector_id),
            "inspector_name": inspector.full_name,
            "inspector_email": inspector.email,
            "period_start": str(start_date) if start_date else "all time",
            "period_end": str(end_date) if end_date else "all time",
            "total_inspections": total,
            "status_breakdown": status_breakdown,
            "customers_served": customers_served,
            "completion_rate_pct": (
                round(status_breakdown.get("COMPLETED", 0) / total * 100, 1)
                if total > 0 else 0.0
            ),
        }

    # -------------------------------------------------------------------------
    # INSPECTORS LEADERBOARD — Ranking across all inspectors
    # -------------------------------------------------------------------------

    async def get_inspectors_leaderboard(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Ranks inspectors by total inspections in the given period.
        """
        return await self.user_repo.get_inspectors_performance(
            start_date=start_date, end_date=end_date, limit=limit
        )

    # -------------------------------------------------------------------------
    # TREND REPORT — Time-series data for charts
    # -------------------------------------------------------------------------

    async def get_trend_report(
        self,
        start_date: date,
        end_date: date,
    ) -> Dict[str, Any]:
        """
        Returns daily inspection volume + new vs returning customer split
        for the given period. Feeds line charts and area charts on the dashboard.
        """
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date.",
            )

        daily_trend = await self.inspection_repo.get_daily_inspection_trend(start_date, end_date)
        customer_metrics = await self.customer_repo.get_customers_served_metrics(start_date, end_date)
        status_breakdown = await self.inspection_repo.get_status_breakdown(start_date, end_date)
        condition_dist = await self.inspection_repo.get_overall_condition_distribution(
            start_date, end_date
        )

        return {
            "period_start": str(start_date),
            "period_end": str(end_date),
            "daily_inspection_trend": daily_trend,
            "customer_metrics": {
                "total_served": customer_metrics["total_served"],
                "new_customers": customer_metrics["new"],
                "returning_customers": customer_metrics["returning"],
            },
            "inspection_status_breakdown": status_breakdown,
            "condition_distribution": condition_dist,
        }

    # -------------------------------------------------------------------------
    # FAULT INTELLIGENCE — What is commonly wrong with cars
    # -------------------------------------------------------------------------

    async def get_fault_intelligence(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> Dict[str, Any]:
        """
        Surfaces the most common fault patterns across all inspections.
        Pairs the raw fault list with the severity ratio for context.
        """
        common_faults = await self.inspection_repo.get_most_common_faults(
            start_date, end_date, limit=limit
        )
        severity = await self.inspection_repo.get_issue_severity_ratio(start_date, end_date)

        return {
            "period_start": str(start_date) if start_date else "all time",
            "period_end": str(end_date) if end_date else "all time",
            "top_faults": common_faults,
            "severity_summary": severity,
        }

    # -------------------------------------------------------------------------
    # CUSTOMER INSIGHTS — Top customers and activity
    # -------------------------------------------------------------------------

    async def get_customer_insights(self, limit: int = 10) -> Dict[str, Any]:
        """
        Top customers + today/week/month engagement stats.
        """
        top_customers = await self.customer_repo.get_top_customers(limit=limit)
        dashboard = await self.customer_repo.get_performance_dashboard()

        return {
            "top_customers_by_inspections": top_customers,
            "engagement": dashboard,
        }
