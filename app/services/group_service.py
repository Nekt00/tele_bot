from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import ContextTypes

from app.repositories import GroupRepository
from app.models import BotGroup
from .base import BaseService


class GroupService(BaseService):
    """Сервис для управления группами бота"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.group_repo = GroupRepository(session)
    
    async def register_group(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        title: str,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """Зарегистрировать группу (когда бот добавлен)"""
        group = await self.group_repo.create_or_update(
            chat_id=chat_id,
            title=title,
            username=username
        )
        
        if "bot_groups" not in context.bot_data:
            context.bot_data["bot_groups"] = {}
        
        context.bot_data["bot_groups"][chat_id] = {
            'title': title,
            'username': username
        }
        
        return {
            "success": True,
            "chat_id": group.chat_id,
            "title": group.title,
            "username": group.username,
            "is_active": group.is_active
        }
    
    async def get_active_groups(self) -> List[BotGroup]:
        """Получить все активные группы"""
        return await self.group_repo.get_active_groups()
    
    async def get_group_info(self, chat_id: int) -> Optional[Dict[str, Any]]:
        """Получить информацию о группе"""
        group = await self.group_repo.get_by_chat_id(chat_id)
        if not group:
            return None
        return {
            "chat_id": group.chat_id,
            "title": group.title,
            "username": group.username,
            "is_active": group.is_active,
        }
