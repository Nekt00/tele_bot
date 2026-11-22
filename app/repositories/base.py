from typing import TypeVar, Generic, Type, Optional, List
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func

from app.models import Base

ModelType = TypeVar("ModelType", bound=Base)


class BaseRepository(Generic[ModelType]):
    """Базовый репозиторий с CRUD операциями"""
    
    def __init__(self, model: Type[ModelType], session: AsyncSession):
        self.model = model
        self.session = session
    
    async def create(self, **kwargs) -> ModelType:
        """Создать одну запись"""
        instance = self.model(**kwargs)
        self.session.add(instance)
        await self.session.flush()
        return instance
    
    async def get(self, **filters) -> Optional[ModelType]:
        """Получить одну запись по фильтрам"""
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar_one_or_none()
    
    async def get_all(self, **filters) -> List[ModelType]:
        """Получить все записи по фильтрам"""
        query = select(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def delete(self, **filters) -> int:
        """Удалить записи по фильтрам"""
        result = await self.session.execute(
            select(self.model).filter_by(**filters)
        )
        instances = result.scalars().all()
        for instance in instances:
            await self.session.delete(instance)
        await self.session.flush()
        return len(instances)
    
    async def count(self, **filters) -> int:
        """Подсчитать количество записей"""
        query = select(func.count()).select_from(self.model).filter_by(**filters)
        result = await self.session.execute(query)
        return result.scalar() or 0

    async def update_one(self, pk_value, **kwargs) -> Optional[ModelType]:
        """Обновить одну запись по первичному ключу."""
        instance = await self.session.get(self.model, pk_value)
        if not instance:
            return None

        for field, value in kwargs.items():
            setattr(instance, field, value)

        await self.session.flush()
        return instance
