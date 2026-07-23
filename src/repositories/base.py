"""
Base repository with generic CRUD operations.

Provides reusable database operations that can be inherited by specific repositories.
"""

from typing import Generic, TypeVar, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, update, func, delete
from sqlalchemy.orm import DeclarativeBase
from uuid import UUID
from datetime import datetime, timezone

ModelType = TypeVar("ModelType", bound=DeclarativeBase)

class BaseRepository(Generic[ModelType]):
    """
    Generic Repository for CRUD Operations.
    """

    def __init__(self, model: Type[ModelType], db: AsyncSession):
        """
        Initialize the repository with model class and database session.
        """
        self.model = model
        self.db_session = db

    async def create(self, **kwargs) -> ModelType:
        """
        Create a new Record
        """
        instance = self.model(**kwargs)
        self.db_session.add(instance)
        await self.db_session.flush()
        await self.db_session.refresh(instance)
        return await self.get_by_id(instance.id)
    
    async def get_by_id(self, id: UUID) -> Optional[ModelType]:
        """
        Retrieve a record by its UUID.
        """
        query = select(self.model).where(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(
            self,
            skip: int = 0,
            limit: int = 100,
            include_deleted: bool = False
    ) -> tuple[List[ModelType], int]:
        """
        Get all records with pagination
        """
        query = select(self.model)
        count_query = select(func.count(self.model.id))

        # Filter out soft-deleted records unless requested
        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
            count_query = count_query.where(self.model.deleted_at.is_(None))

        # Get total count
        total_result = await self.db_session.execute(count_query)
        total = total_result.scalar_one()

        query = query.offset(skip).limit(limit)

        result = await self.db_session.execute(query)
        items = result.scalars().all()

        return list(items), total  

    async def update(self, id: UUID, **kwargs) -> Optional[ModelType]:
        """
        Updated a record by ID.
        """  
        instance = await self.get_by_id(id)
        if not instance:
            return None
        
        # Update fields
        for key, value in kwargs.items():
            if hasattr(instance, key):
                setattr(instance, key, value)

        if hasattr(instance, 'updated_at'):
            instance.updated_at = datetime.now(timezone.utc)

        await self.db_session.flush()
        await self.db_session.refresh(instance)
        return await self.get_by_id(instance.id)

    async def soft_delete(self, id: UUID) -> bool:
        """
        Soft delete a record by setting deleted_at timestamp
        """
        instance = await self.get_by_id(id)
        if not instance:
            return False

        if hasattr(instance, 'deleted_at'):
            instance.deleted_at = datetime.now(timezone.utc)
            await self.db_session.flush()
            return True
        
        return False
    
    async def hard_delete(self, id: UUID) -> bool:
        """
        Hard delete a record from database.
        """
        query = delete(self.model).where(self.model.id == id)
        result = await self.db_session.execute(query)
        await self.db_session.flush()
        return result.rowcount > 0

    async def exists(self, id: UUID) -> bool:
        """
        Check if a record exists by ID.
        """ 
        query = select(func.count(self.model.id)).where(self.model.id == id)
        if hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))
        result = await self.db_session.execute(query)
        count = result.scalar_one()
        return count > 0

    async def count(self, include_deleted: bool = False) -> int:
        """
        Count total records
        """
        query = select(func.count(self.model.id))

        if not include_deleted and hasattr(self.model, 'deleted_at'):
            query = query.where(self.model.deleted_at.is_(None))

        result = await self.db_session.execute(query)
        return result.scalar_one()
    
    

