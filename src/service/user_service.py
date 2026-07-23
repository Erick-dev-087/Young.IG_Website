"""
User Service — Young IG Auto Inspection System

Handles all user management operations including CRUD, admin-level actions
(approval, role assignment, suspension), and inspector analytics.
"""

from uuid import UUID
from datetime import date, datetime, timezone
from typing import List, Optional, Dict, Any, Tuple

from fastapi import HTTPException, status
from sqlalchemy.ext.asyncio import AsyncSession
from loguru import logger

from ..model import User
from ..repositories.user_repository import UserRepository
from ..Schemas.user import UserCreate, UserUpdate, UserAdminUpdate, UserResponse
from ..enums import UserRole, UserStatus
from ..utils.security import hash_password


class UserService:
    """
    Business logic for user management.
    Separates admin-only operations from general user operations.
    """

    def __init__(self, db: AsyncSession):
        self.db = db
        self.user_repo = UserRepository(db)

    # ------------------------------------------------------------------
    # CRUD — General user operations
    # ------------------------------------------------------------------

    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> Tuple[List[User], int]:
        """Paginated list of all users."""
        return await self.user_repo.get_all(skip=skip, limit=limit, include_deleted=include_deleted)

    async def get_by_id(self, user_id: UUID) -> User:
        """Fetch a single user or raise 404."""
        user = await self.user_repo.get_by_id(user_id)
        if not user:
            raise HTTPException(
                status_code=status.HTTP_404_NOT_FOUND,
                detail="User not found.",
            )
        return user

    async def get_by_email(self, email: str) -> Optional[User]:
        return await self.user_repo.get_by_email(email)

    async def get_by_phone(self, phone: str) -> Optional[User]:
        return await self.user_repo.get_by_phone(phone)

    async def update_profile(self, user_id: UUID, data: UserUpdate) -> User:
        """
        Allows a user to update their own profile fields (name, email, phone).
        Validates email uniqueness if email is being changed.
        """
        user = await self.get_by_id(user_id)

        update_data = data.model_dump(exclude_unset=True)

        # If changing email, ensure it's not already taken by someone else
        if "email" in update_data and update_data["email"] != user.email:
            if await self.user_repo.check_email_exists(update_data["email"]):
                raise HTTPException(
                    status_code=status.HTTP_409_CONFLICT,
                    detail="A user with this email already exists.",
                )

        updated = await self.user_repo.update(user_id, **update_data)
        if not updated:
            raise HTTPException(
                status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Failed to update user.",
            )
        logger.info(f"User profile updated: {updated.email}")
        return updated

    async def soft_delete(self, user_id: UUID, deleted_by: Optional[UUID] = None) -> Dict[str, str]:
        """
        Soft-deletes a user. Optionally records who performed the deletion.
        """
        user = await self.get_by_id(user_id)

        update_fields = {"deleted_at": datetime.now(timezone.utc)}
        if deleted_by:
            update_fields["deleted_by"] = deleted_by

        await self.user_repo.update(user_id, **update_fields)
        logger.info(f"User soft-deleted: {user.email} (by {deleted_by})")
        return {"message": f"User {user.email} has been deactivated."}

    # ------------------------------------------------------------------
    # ADMIN — Approval, role assignment, status changes
    # ------------------------------------------------------------------

    async def approve_user(self, user_id: UUID, admin_id: UUID) -> User:
        """
        Admin approves a PENDING user registration.
        Sets status to APPROVED and records who approved and when.
        """
        user = await self.get_by_id(user_id)

        if user.status != UserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot approve user with status '{user.status.value}'. Only PENDING users can be approved.",
            )

        updated = await self.user_repo.update(
            user_id,
            status=UserStatus.APPROVED,
            approved_by=admin_id,
            approved_at=datetime.now(timezone.utc),
        )
        logger.info(f"User approved: {user.email} by admin {admin_id}")
        return updated

    async def reject_user(self, user_id: UUID, admin_id: UUID) -> User:
        """
        Admin rejects a PENDING user registration.
        """
        user = await self.get_by_id(user_id)

        if user.status != UserStatus.PENDING:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"Cannot reject user with status '{user.status.value}'. Only PENDING users can be rejected.",
            )

        updated = await self.user_repo.update(user_id, status=UserStatus.REJECTED)
        logger.info(f"User rejected: {user.email} by admin {admin_id}")
        return updated

    async def suspend_user(self, user_id: UUID, admin_id: UUID) -> User:
        """
        Admin suspends an active user.
        """
        user = await self.get_by_id(user_id)

        if user.status == UserStatus.SUSPENDED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already suspended.",
            )

        updated = await self.user_repo.update(user_id, status=UserStatus.SUSPENDED)
        logger.info(f"User suspended: {user.email} by admin {admin_id}")
        return updated

    async def reactivate_user(self, user_id: UUID, admin_id: UUID) -> User:
        """
        Admin reactivates a suspended or rejected user back to APPROVED.
        """
        user = await self.get_by_id(user_id)

        if user.status == UserStatus.APPROVED:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail="User is already active.",
            )

        updated = await self.user_repo.update(user_id, status=UserStatus.APPROVED)
        logger.info(f"User reactivated: {user.email} by admin {admin_id}")
        return updated

    async def assign_role(self, user_id: UUID, role: UserRole, admin_id: UUID) -> User:
        """
        Admin assigns a role to a user.
        """
        user = await self.get_by_id(user_id)

        if user.role == role:
            raise HTTPException(
                status_code=status.HTTP_400_BAD_REQUEST,
                detail=f"User already has the role '{role.value}'.",
            )

        updated = await self.user_repo.update(user_id, role=role)
        logger.info(f"Role changed for {user.email}: {user.role.value} -> {role.value} by admin {admin_id}")
        return updated

    async def get_by_role(
        self, role: UserRole, skip: int = 0, limit: int = 100
    ) -> Tuple[List[User], int]:
        """Get users filtered by role (e.g. all inspectors)."""
        return await self.user_repo.get_by_role(role, skip=skip, limit=limit)

    async def get_by_status(
        self, user_status: UserStatus, skip: int = 0, limit: int = 100
    ) -> Tuple[List[User], int]:
        """Get users filtered by status (e.g. all pending registrations)."""
        return await self.user_repo.get_by_status(user_status, skip=skip, limit=limit)

    async def get_pending_registrations(
        self, skip: int = 0, limit: int = 100
    ) -> Tuple[List[User], int]:
        """Convenience method: gets all users awaiting admin approval."""
        return await self.user_repo.get_by_status(UserStatus.PENDING, skip=skip, limit=limit)

    # ------------------------------------------------------------------
    # ANALYTICS — Inspector productivity metrics
    # ------------------------------------------------------------------

    async def get_inspector_stats(
        self,
        inspector_id: UUID,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
    ) -> Dict[str, Any]:
        """
        Returns a combined stats object for a single inspector:
        total inspections + status breakdown for the given period.
        """
        inspector = await self.get_by_id(inspector_id)

        total = await self.user_repo.get_inspector_inspection_count(
            inspector_id, start_date, end_date
        )
        breakdown = await self.user_repo.get_inspector_status_breakdown(
            inspector_id, start_date, end_date
        )

        return {
            "inspector_id": str(inspector_id),
            "inspector_name": inspector.full_name,
            "period_start": str(start_date) if start_date else None,
            "period_end": str(end_date) if end_date else None,
            "total_inspections": total,
            "status_breakdown": breakdown,
        }

    async def get_inspectors_leaderboard(
        self,
        start_date: Optional[date] = None,
        end_date: Optional[date] = None,
        limit: int = 10,
    ) -> List[Dict[str, Any]]:
        """
        Ranking of inspectors by inspection count.
        Used for the admin dashboard leaderboard.
        """
        return await self.user_repo.get_inspectors_performance(
            start_date=start_date, end_date=end_date, limit=limit
        )
