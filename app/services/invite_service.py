from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import ContextTypes

from app.repositories import GroupRepository
from .base import BaseService


class InviteService(BaseService):
    """Сервис для управления пригласительными ссылками"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.group_repo = GroupRepository(session)
    
    async def create_invite_link(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        member_limit: int = 1
    ) -> Optional[str]:
        """
        Создать пригласительную ссылку в группу
        """
        try:
            link = await context.bot.create_chat_invite_link(
                chat_id=chat_id,
                member_limit=member_limit,
                expire_date=None
            )
            
            # Сохраняем ссылку в БД
            await self.group_repo.update_invite_link(chat_id, link.invite_link)
            
            return link.invite_link
        except Exception as e:
            print(f"Ошибка создания ссылки: {e}")
            return None
    
    async def get_cached_invite_link(self, chat_id: int) -> Optional[str]:
        """
        Получить кэшированную ссылку из БД
        """
        group = await self.group_repo.get_by_chat_id(chat_id)
        return group.invite_link if group else None
    
    async def get_or_create_invite_link(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        member_limit: int = 1
    ) -> Optional[str]:
        """
        Получить существующую ссылку или создать новую
        """
        # Пробуем получить из кэша
        cached_link = await self.get_cached_invite_link(chat_id)
        
        if cached_link:
            return cached_link
        
        # Создаём новую
        return await self.create_invite_link(context, chat_id, member_limit)
    
    async def update_group_info(
        self,
        chat_id: int,
        title: str,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Обновить информацию о группе
        """
        group = await self.group_repo.create_or_update(
            chat_id=chat_id,
            title=title,
            username=username
        )
        
        return {
            "chat_id": group.chat_id,
            "title": group.title,
            "username": group.username,
            "is_active": group.is_active
        }
    
    async def deactivate_group(self, chat_id: int) -> bool:
        """
        Деактивировать группу
        """
        return await self.group_repo.deactivate_group(chat_id)
    
    async def activate_group(self, chat_id: int) -> bool:
        """
        Активировать группу
        """
        return await self.group_repo.activate_group(chat_id)