"""
Customer Service — Young IG Auto Inspection System

Handles customer CRUD, history retrieval, and all business analytics
(served metrics, performance dashboard, top customers).
"""

from uuid import UUID
from datetime import date
from typing import List, Optional, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..model import Customer
from ..repositories.customer_repository import CustomerRepository
from ..Schemas.customer import CustomerCreate, CustomerUpdate
from ..enums import CustomerType


class CustomerService:
    """
    Business logic for customer management and analytics.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.customer_repo = CustomerRepository(db)

    # ------------------------------------------------------------------
    # CRUD
    # ------------------------------------------------------------------

    async def create(self, data: CustomerCreate) -> Customer:
        """
        Register a new customer. Prevents duplicate emails if provided.
        """
        customer_data = data.model_dump()

        # Check for duplicate email only if one was provided
        if customer_data.get("email"):
            existing = await self.customer_repo.get_by_email(customer_data["email"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A customer with this email already exists.",
                )

        # Check for duplicate phone only if one was provided
        if customer_data.get("phone"):
            existing = await self.customer_repo.get_by_phone(customer_data["phone"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A customer with this phone number already exists.",
                )

        customer = await self.customer_repo.create(**customer_data)
        logger.info(f"Customer created: {customer.full_name}")
        return customer

    async def get_or_create(self, data: CustomerCreate) -> Customer:
        """
        Returns the existing customer if email or phone matches,
        otherwise creates a new one. This powers the 'Option 1' 
        inspection initialization workflow.
        """
        customer_data = data.model_dump()

        # Check existing by email
        if customer_data.get("email"):
            existing = await self.customer_repo.get_by_email(customer_data["email"])
            if existing:
                return existing

        # Check existing by phone
        if customer_data.get("phone"):
            existing = await self.customer_repo.get_by_phone(customer_data["phone"])
            if existing:
                return existing

        customer = await self.customer_repo.create(**customer_data)
        logger.info(f"Customer registered via get_or_create: {customer.full_name}")
        return customer

    async def get_all(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Customer], int]:
        return await self.customer_repo.get_all(skip=skip, limit=limit)

    async def get_by_id(self, customer_id: UUID) -> Customer:
        customer = await self.customer_repo.get_by_id(customer_id)
        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )
        return customer

    async def get_by_email(self, email: str) -> Optional[Customer]:
        return await self.customer_repo.get_by_email(email)

    async def get_by_phone(self, phone: str) -> Optional[Customer]:
        return await self.customer_repo.get_by_phone(phone)

    async def get_by_type(
        self, customer_type: CustomerType, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Customer], int]:
        return await self.customer_repo.get_by_type(customer_type, skip=skip, limit=limit)

    async def update(self, customer_id: UUID, data: CustomerUpdate) -> Customer:
        """
        Update customer details. Validates email uniqueness if email is changing.
        """
        customer = await self.get_by_id(customer_id)
        update_data = data.model_dump(exclude_unset=True)

        if not update_data:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="No fields to update.",
            )

        # If email is being changed, ensure uniqueness
        if "email" in update_data and update_data["email"] != customer.email:
            existing = await self.customer_repo.get_by_email(update_data["email"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A customer with this email already exists.",
                )

        # If phone is being changed, ensure uniqueness
        if "phone" in update_data and update_data["phone"] != customer.phone:
            existing = await self.customer_repo.get_by_phone(update_data["phone"])
            if existing:
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A customer with this phone number already exists.",
                )

        updated = await self.customer_repo.update(customer_id, **update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update customer.",
            )
        logger.info(f"Customer updated: {updated.full_name}")
        return updated

    async def delete(self, customer_id: UUID) -> Dict[str, str]:
        """Soft-delete a customer if the model supports it, otherwise hard-delete."""
        customer = await self.get_by_id(customer_id)

        if hasattr(Customer, "deleted_at"):
            await self.customer_repo.soft_delete(customer_id)
        else:
            await self.customer_repo.hard_delete(customer_id)

        logger.info(f"Customer deleted: {customer.full_name}")
        return {"message": f"Customer '{customer.full_name}' has been removed."}

    # ------------------------------------------------------------------
    # HISTORY & RELATIONSHIPS
    # ------------------------------------------------------------------

    async def get_customer_history(self, customer_id: UUID) -> Dict[str, Any]:
        """
        Retrieves the full history of a customer including all their inspections.
        Returns a structured dict ready for the API response.
        """
        customer, inspections = await self.customer_repo.get_customer_history(customer_id)

        if not customer:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="Customer not found.",
            )

        return {
            "customer": customer,
            "total_inspections": len(inspections),
            "inspections": inspections,
        }

    async def get_customers_by_inspector(
        self, inspector_id: UUID, skip: int = 0, limit: int = 100
    ) -> Tuple[List[Customer], int]:
        """Get all distinct customers served by a specific inspector."""
        return await self.customer_repo.get_by_inspector(inspector_id, skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # ANALYTICS — Business insights
    # ------------------------------------------------------------------

    async def get_performance_dashboard(self) -> Dict[str, int]:
        """
        High-level dashboard stats: total customers, served today/week/month.
        """
        return await self.customer_repo.get_performance_dashboard()

    async def get_served_metrics(
        self, start_date: date, end_date: date
    ) -> Dict[str, Any]:
        """
        Metrics for a specific timeframe: total served, new vs returning.
        """
        if start_date > end_date:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="start_date cannot be after end_date.",
            )

        metrics = await self.customer_repo.get_customers_served_metrics(start_date, end_date)

        return {
            "timeframe_start": str(start_date),
            "timeframe_end": str(end_date),
            "total_customers_served": metrics["total_served"],
            "new_customers": metrics["new"],
            "returning_customers": metrics["returning"],
        }

    async def get_top_customers(self, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Ranking of top customers by inspection count.
        Useful for loyalty insights and VIP identification.
        """
        return await self.customer_repo.get_top_customers(limit=limit)
