from typing import Optional, List, Dict, Any
from datetime import datetime, timezone
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import BotGroup
from .base import BaseRepository


class GroupRepository(BaseRepository[BotGroup]):
    """Репозиторий для работы с группами бота"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(BotGroup, session)
    
    async def get_by_chat_id(self, chat_id: int) -> Optional[BotGroup]:
        """Получить группу по ID чата"""
        return await self.get(chat_id=chat_id)
    
    async def create_or_update(
        self, 
        chat_id: int, 
        title: str,
        username: Optional[str] = None,
        invite_link: Optional[str] = None
    ) -> BotGroup:
        """Создать или обновить группу"""
        existing = await self.get_by_chat_id(chat_id)
        
        if existing:
            existing.title = title
            if username:
                existing.username = username
            if invite_link:
                existing.invite_link = invite_link
            await self.session.flush()
            return existing
        else:
            return await self.create(
                chat_id=chat_id,
                title=title,
                username=username,
                invite_link=invite_link,
                is_active=True,
                member_count=0
            )
    
    async def get_active_groups(self) -> List[BotGroup]:
        """Получить все активные группы"""
        return await self.get_all(is_active=True)
    
    async def get_inactive_groups(self) -> List[BotGroup]:
        """Получить все неактивные группы"""
        return await self.get_all(is_active=False)
    
    async def deactivate_group(self, chat_id: int) -> bool:
        """Деактивировать группу"""
        group = await self.update_one(chat_id, is_active=False)
        return group is not None
    
    async def activate_group(self, chat_id: int) -> bool:
        """Активировать группу"""
        group = await self.update_one(chat_id, is_active=True)
        return group is not None
    
    async def update_member_count(self, chat_id: int, count: int) -> Optional[BotGroup]:
        """Обновить количество участников"""
        return await self.update_one(chat_id, member_count=count)
    
    async def update_invite_link(self, chat_id: int, invite_link: str) -> Optional[BotGroup]:
        """Обновить пригласительную ссылку"""
        return await self.update_one(chat_id, invite_link=invite_link)
    
    async def update_activity(self, chat_id: int) -> Optional[BotGroup]:
        """Обновить время последней активности"""
        return await self.update_one(chat_id, updated_at=datetime.now(timezone.utc))
    
    async def get_groups_with_stats(self) -> List[Dict[str, Any]]:
        """Получить группы со статистикой"""
        groups = await self.get_active_groups()
        
        result = []
        for group in groups:
            result.append({
                "chat_id": group.chat_id,
                "title": group.title,
                "is_active": group.is_active,
                "member_count": group.member_count or 0,
                "created_at": group.created_at
            })
        
        return result
