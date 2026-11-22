from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select

from app.models import UserSession
from .base import BaseRepository


class SessionRepository(BaseRepository[UserSession]):
    """Репозиторий для работы с сессиями пользователей"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(UserSession, session)
    
    async def get_by_user_id(self, user_id: int) -> Optional[UserSession]:
        """Получить сессию по ID пользователя"""
        result = await self.session.execute(
            select(UserSession).where(UserSession.user_id == user_id)
        )
        return result.scalar_one_or_none()
    
    async def create_or_update(
        self, 
        user_id: int, 
        step: int = 0, 
        data: Optional[Dict[str, Any]] = None
    ) -> UserSession:
        """Создать или обновить сессию"""
        existing = await self.get_by_user_id(user_id)
        
        if existing:
            existing.step = step
            if data is not None:
                existing.data = data
            await self.session.flush()
            return existing
        new_session = UserSession(
            user_id=user_id,
            step=step,
            data=data or {}
        )
        self.session.add(new_session)
        await self.session.flush()
        return new_session
    
    async def update_step(self, user_id: int, step: int) -> Optional[UserSession]:
        """Обновить только шаг сессии"""
        session = await self.get_by_user_id(user_id)
        if session:
            session.step = step
            await self.session.flush()
        return session
    
    async def update_data(self, user_id: int, data: Dict[str, Any]) -> Optional[UserSession]:
        """Обновить данные сессии"""
        session = await self.get_by_user_id(user_id)
        if session:
            session.data = data
            await self.session.flush()
        return session
    
    async def delete_by_user_id(self, user_id: int) -> bool:
        """Удалить сессию пользователя"""
        session = await self.get_by_user_id(user_id)
        if session:
            await self.session.delete(session)
            await self.session.flush()
            return True
        return False
    
    async def get_all(self) -> list[UserSession]:
        """Получить все сессии"""
        result = await self.session.execute(select(UserSession))
        return list(result.scalars().all())
