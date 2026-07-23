from sqlalchemy import select, func, and_, desc, distinct
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload
from uuid import UUID
from datetime import date, datetime, timedelta
from typing import List, Tuple, Optional, Dict, Any

from .base import BaseRepository
from src.model import Customer, Inspection
from src.enums import CustomerType

class CustomerRepository(BaseRepository[Customer]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(Customer, db_session)
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False
    )->tuple[List[Customer], int]:
        query = select(Customer)
        count_query = select(func.count(Customer.id))
        if not include_deleted and hasattr(Customer, 'deleted_at'):
            query = query.where(Customer.deleted_at.is_(None))
            count_query = count_query.where(Customer.deleted_at.is_(None))
        total = await self.db_session.execute(count_query)
        total = total.scalar_one()
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all(), total

    async def get_by_id(self, id: UUID):
        query = select(Customer).where(Customer.id == id)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str):
        query = select(Customer).where(Customer.email == email)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_phone(self, phone: str) -> Optional[Customer]:
        query = select(Customer).where(Customer.phone == phone)
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_type(
        self,
        customer_type: CustomerType,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Customer], int]:
        query = select(Customer).where(Customer.customer_type == customer_type)
        count_query = select(func.count(Customer.id)).where(Customer.customer_type == customer_type)
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0
        
    async def get_by_inspector(
        self,
        inspector_id: UUID,
        skip: int = 0,
        limit: int = 100
    ) -> Tuple[List[Customer], int]:
        """Get all distinct customers that a specific inspector has served."""
        query = (
            select(Customer)
            .join(Inspection, Inspection.customer_id == Customer.id)
            .where(Inspection.inspector_id == inspector_id)
            .distinct()
        )
        count_query = (
            select(func.count(distinct(Customer.id)))
            .join(Inspection, Inspection.customer_id == Customer.id)
            .where(Inspection.inspector_id == inspector_id)
        )
        
        total = await self.db_session.scalar(count_query)
        result = await self.db_session.execute(query.offset(skip).limit(limit))
        return list(result.scalars().all()), total or 0 

    async def get_customer_history(self, customer_id: UUID) -> Tuple[Optional[Customer], List[Inspection]]:
        """
        Retrieves a customer's entire history, including all their past inspections,
        vehicles, and results.
        """
        query = (
            select(Customer)
            .where(Customer.id == customer_id)
            .options(
                selectinload(Customer.inspections).selectinload(Inspection.vehicle),
                selectinload(Customer.inspections).selectinload(Inspection.inspector),
                selectinload(Customer.inspections).selectinload(Inspection.results)
            )
        )
        result = await self.db_session.execute(query)
        customer = result.scalar_one_or_none()
        
        if not customer:
            return None, []
            
        # Sort inspections by date descending manually since selectinload doesn't easily order
        inspections = sorted(customer.inspections, key=lambda x: x.inspection_date, reverse=True)
        return customer, inspections

    async def get_customers_served_metrics(self, start_date: date, end_date: date) -> Dict[str, Any]:
        """
        Returns metrics about customers served in a specific timeframe.
        Calculates how many are 'new' (first inspection) vs 'returning' (had inspections before).
        """
        # Get all distinct customers served in the timeframe
        served_query = (
            select(distinct(Inspection.customer_id))
            .where(Inspection.inspection_date >= start_date)
            .where(Inspection.inspection_date <= end_date)
            .where(Inspection.customer_id.isnot(None))
        )
        served_result = await self.db_session.execute(served_query)
        customer_ids_served = [row for row in served_result.scalars().all()]
        
        if not customer_ids_served:
            return {"total_served": 0, "new": 0, "returning": 0}
            
        # For those customers, check if their FIRST inspection was inside this timeframe
        # If it was, they are new. If it was before start_date, they are returning.
        first_inspection_query = (
            select(Inspection.customer_id, func.min(Inspection.inspection_date).label('first_date'))
            .where(Inspection.customer_id.in_(customer_ids_served))
            .group_by(Inspection.customer_id)
        )
        first_result = await self.db_session.execute(first_inspection_query)
        
        new_customers = 0
        returning_customers = 0
        
        for row in first_result.all():
            if row.first_date >= start_date:
                new_customers += 1
            else:
                returning_customers += 1
                
        return {
            "total_served": len(customer_ids_served),
            "new": new_customers,
            "returning": returning_customers
        }

    async def get_performance_dashboard(self) -> Dict[str, int]:
        """
        High-level business metrics for the dashboard showing daily, weekly, and monthly activity.
        """
        today = date.today()
        start_of_week = today - timedelta(days=today.weekday())
        start_of_month = today.replace(day=1)
        
        # Total customers in system
        total_customers = await self.db_session.scalar(select(func.count(Customer.id)))
        
        # Served Today
        today_query = select(func.count(distinct(Inspection.customer_id))).where(Inspection.inspection_date == today)
        served_today = await self.db_session.scalar(today_query)
        
        # Served This Week
        week_query = select(func.count(distinct(Inspection.customer_id))).where(Inspection.inspection_date >= start_of_week)
        served_week = await self.db_session.scalar(week_query)
        
        # Served This Month
        month_query = select(func.count(distinct(Inspection.customer_id))).where(Inspection.inspection_date >= start_of_month)
        served_month = await self.db_session.scalar(month_query)
        
        return {
            "total_customers_in_system": total_customers or 0,
            "customers_served_today": served_today or 0,
            "customers_served_this_week": served_week or 0,
            "customers_served_this_month": served_month or 0
        }

    async def get_top_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Get a ranking of top customers based on how many inspections they've booked.
        """
        query = (
            select(
                Customer.id,
                Customer.full_name,
                Customer.email,
                Customer.phone,
                func.count(Inspection.id).label('total_inspections')
            )
            .join(Inspection, Inspection.customer_id == Customer.id)
            .group_by(Customer.id)
            .order_by(desc('total_inspections'))
            .limit(limit)
        )
        
        result = await self.db_session.execute(query)
        
        top_customers = []
        for row in result.all():
            top_customers.append({
                "customer_id": row.id,
                "full_name": row.full_name,
                "email": row.email,
                "phone": row.phone,
                "total_inspections": row.total_inspections
            })
            
        return top_customers