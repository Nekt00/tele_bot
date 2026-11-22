from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import SessionRepository
from .base import BaseService


class SessionService(BaseService):
    """Сервис для управления сессиями пользователей (с БД)"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.session_repo = SessionRepository(session)
    
    async def get_or_create_session(
        self, 
        user_id: int,
        mode: str = "quiz",
        group_chat_id: Optional[int] = None,
        first_name: Optional[str] = None,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Получить или создать сессию пользователя"""
        session = await self.session_repo.get_by_user_id(user_id)
        
        if not session:
            session_data = {
                "mode": mode,
                "step": 0,
                "group_chat_id": group_chat_id,
                "first_name": first_name,
                "username": username,
                "user_id": user_id,
                "data": {},
                "last_question_id": None
            }
            session = await self.session_repo.create_or_update(
                user_id=user_id,
                step=0,
                data=session_data
            )
            return session.data
        
        if group_chat_id and not session.data.get("group_chat_id"):
            session.data["group_chat_id"] = group_chat_id
            session.data["first_name"] = first_name or session.data.get("first_name")
            session.data["username"] = username or session.data.get("username")
            await self.session_repo.update_data(user_id, session.data)
        
        return session.data
    
    async def update_session_step(self, user_id: int, step: int) -> None:
        await self.session_repo.update_step(user_id, step)
    
    async def update_session_data(self, user_id: int, data: Dict[str, Any]) -> None:
        await self.session_repo.update_data(user_id, data)
    
    async def get_current_step(self, user_id: int) -> int:
        session = await self.session_repo.get_by_user_id(user_id)
        return session.step if session else 0
    
    async def get_session_data(self, user_id: int) -> Optional[Dict[str, Any]]:
        session = await self.session_repo.get_by_user_id(user_id)
        return session.data if session else None
    
    async def clear_session(self, user_id: int) -> None:
        await self.session_repo.delete_by_user_id(user_id)
    
    async def has_active_quiz(self, user_id: int) -> bool:
        session = await self.session_repo.get_by_user_id(user_id)
        if not session:
            return False
        return session.data.get("mode") == "quiz" and session.step < 5
    
    async def load_all_sessions_to_cache(self) -> Dict[int, Dict[str, Any]]:
        all_sessions = await self.session_repo.get_all()
        return {session.user_id: session.data for session in all_sessions}
