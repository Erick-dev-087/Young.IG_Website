from sqlalchemy import select, func, desc, and_
from sqlalchemy.ext.asyncio import AsyncSession
from uuid import UUID
from datetime import datetime, date
from typing import List, Optional, Tuple, Dict, Any

from .base import BaseRepository
from src.model import User, Customer, Inspection
from src.enums import UserRole, UserStatus, InspectionStatus


class UserRepository(BaseRepository[User]):
    def __init__(self, db_session: AsyncSession):
        super().__init__(User, db_session)
    
    async def get_all(
        self,
        skip: int = 0,
        limit: int = 100,
        include_deleted: bool = False,
    ) -> tuple[List[User], int]:
        """
        Get all users with pagination
        """  
        query = select(User)
        count_query = select(func.count(User.id))
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
            count_query = count_query.where(User.deleted_at.is_(None))
        
        total = await self.db_session.execute(count_query)
        total = total.scalar_one()
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all(), total

    async def get_by_id(self, id:UUID):
        """
        Get a user by their id
        """      
        query = select(User).where(User.id == id)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()

    async def get_by_email(self, email: str) -> Optional[User]:
        """
        Get user by email
        """  
        query = select(User).where(User.email == email)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def check_email_exists(self, email: str) -> bool:
        """
        Check if email exists
        """
        query = select(User.email).where(User.email == email)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def check_phone_exists(self, phone: str) -> bool:
        """
        Check if phone exists
        """
        query = select(User.phone).where(User.phone == phone)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none() is not None
    
    async def get_by_phone(self, phone: str) -> Optional[User]:
        """
        Get user by phone
        """  
        query = select(User).where(User.phone == phone)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_by_role(
        self, 
        role: UserRole,
        skip: int = 0, 
        limit: int = 100) -> tuple[List[User], int]:
        """
        Get user by role
        """
        query = select(User).where(User.role == role)
        count_query = select(func.count(User.id)).where(User.role == role)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
            count_query = count_query.where(User.deleted_at.is_(None))
        
        total = await self.db_session.execute(count_query)
        total = total.scalar_one()
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all(), total

    async def get_by_status(
        self,
        status: UserStatus,
        skip: int = 0,
        limit:int = 100
    ) -> tuple[List[User], int]:
        """
        Get user by status
        """  
        query = select(User).where(User.status == status)
        count_query = select(func.count(User.id)).where(User.status == status)
        if hasattr(User, 'deleted_at'):
            query = query.where(User.deleted_at.is_(None))
            count_query = count_query.where(User.deleted_at.is_(None))
        
        total = await self.db_session.execute(count_query)
        total = total.scalar_one()
        query = query.offset(skip).limit(limit)
        result = await self.db_session.execute(query)
        return result.scalars().all(), total

    async def set_status(
        self,
        user_id:UUID,
        status:UserStatus
    ) -> bool:
        """
        Set user status
        """  
        query = select(User).where(User.id == user_id)
        result = await self.db_session.execute(query)
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.status = status
        await self.db_session.commit()
        return True

    async def set_role(
        self,
        user_id:UUID,
        role:UserRole
    ) -> bool:
        """
        Set user role
        """  
        query = select(User).where(User.id == user_id)
        result = await self.db_session.execute(query)
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.role = role
        await self.db_session.commit()
        return True
    
    async def soft_delete(
        self,
        user_id: UUID
    ) -> bool:
        """
        Soft delete user
        """  
        query = select(User).where(User.id == user_id)
        result = await self.db_session.execute(query)
        user = result.scalar_one_or_none()
        if user is None:
            return False
        user.deleted_at = datetime.utcnow()
        await self.db_session.commit()
        return True
        
    async def get_inspector_inspection_count(
        self, 
        inspector_id: UUID, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> int:
        """
        Get the total number of inspections done by a specific inspector.
        Optionally filter by a date range.
        """
        query = select(func.count(Inspection.id)).where(Inspection.inspector_id == inspector_id)
        
        if start_date:
            query = query.where(Inspection.inspection_date >= start_date)
        if end_date:
            query = query.where(Inspection.inspection_date <= end_date)
            
        result = await self.db_session.execute(query)
        return result.scalar_one()

    async def get_inspector_status_breakdown(
        self, 
        inspector_id: UUID, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None
    ) -> Dict[str, int]:
        """
        Get a breakdown of inspection statuses (e.g., COMPLETED: 5, DRAFT: 2) for an inspector.
        """
        query = (
            select(Inspection.status, func.count(Inspection.id))
            .where(Inspection.inspector_id == inspector_id)
        )
        
        if start_date:
            query = query.where(Inspection.inspection_date >= start_date)
        if end_date:
            query = query.where(Inspection.inspection_date <= end_date)
            
        query = query.group_by(Inspection.status)
        
        result = await self.db_session.execute(query)
        
        # Convert enum objects to string keys in the dictionary if needed
        breakdown = {status.name if hasattr(status, 'name') else str(status): count for status, count in result.all()}
        return breakdown

    async def get_inspectors_performance(
        self, 
        start_date: Optional[date] = None, 
        end_date: Optional[date] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Get a ranking of inspectors based on the total number of inspections they've conducted.
        Returns a list of dicts: [{'inspector_id': ..., 'full_name': ..., 'total_inspections': ...}]
        """
        query = (
            select(
                User.id,
                User.full_name,
                func.count(Inspection.id).label('total_inspections')
            )
            .join(Inspection, Inspection.inspector_id == User.id)
            .where(User.role == UserRole.INSPECTOR)
        )
        
        if start_date:
            query = query.where(Inspection.inspection_date >= start_date)
        if end_date:
            query = query.where(Inspection.inspection_date <= end_date)
            
        query = (
            query.group_by(User.id)
            .order_by(desc('total_inspections'))
            .limit(limit)
        )
        
        result = await self.db_session.execute(query)
        
        performance_data = []
        for row in result.all():
            performance_data.append({
                "inspector_id": row.id,
                "full_name": row.full_name,
                "total_inspections": row.total_inspections
            })
            
        return performance_data



    
