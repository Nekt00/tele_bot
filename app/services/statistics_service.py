from typing import Optional, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import TicketRepository, GroupRepository
from .base import BaseService


class StatisticsService(BaseService):
    """Сервис для сбора статистики"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.ticket_repo = TicketRepository(session)
        self.group_repo = GroupRepository(session)
    
    async def get_group_stats(self, group_chat_id: int) -> Dict[str, Any]:
        """
        Получить статистику по группе
        """
        stats = await self.ticket_repo.get_stats(group_chat_id)
        
        # Получаем информацию о группе
        group = await self.group_repo.get_by_chat_id(group_chat_id)
        
        return {
            "group_title": group.title if group else "Неизвестная группа",
            "group_chat_id": group_chat_id,
            **stats,
            "last_updated": datetime.now()
        }
    
    async def get_global_stats(self) -> Dict[str, Any]:
        """
        Получить глобальную статистику по всем группам
        """
        stats = await self.ticket_repo.get_stats()
        groups = await self.group_repo.get_active_groups()
        
        return {
            "total_groups": len(groups),
            "active_groups": sum(1 for group in groups if group.is_active),
            **stats,
            "last_updated": datetime.now()
        }
    
    async def get_daily_stats(self, group_chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получить статистику по дням за последнюю неделю
        """
        result = {}
        
        for i in range(7):
            date = datetime.now().date() - timedelta(days=i)
            start_date = datetime(date.year, date.month, date.day)
            end_date = start_date + timedelta(days=1)
            
            stats = await self.ticket_repo.get_stats(
                group_chat_id=group_chat_id,
                start_date=start_date,
                end_date=end_date
            )
            
            result[date.isoformat()] = stats["total"]
        
        return result
    
    async def get_user_stats(self, user_id: int) -> Dict[str, Any]:
        """
        Получить статистику по пользователю
        """
        tickets = await self.ticket_repo.get_by_user(user_id)
        
        return {
            "user_id": user_id,
            "total_tickets": len(tickets),
            "quiz_tickets": len([t for t in tickets if t.ticket_type == "quiz"]),
            "free_tickets": len([t for t in tickets if t.ticket_type == "free"]),
            "last_ticket": tickets[0].created_at if tickets else None
        }
    
    async def get_status_distribution(self, group_chat_id: Optional[int] = None) -> Dict[str, Any]:
        """
        Получить распределение обращений по статусам
        """
        stats = await self.ticket_repo.get_stats(group_chat_id)
        
        return {
            "new": stats.get("new_count", 0),
            "in_progress": stats.get("in_progress_count", 0),
            "resolved": stats.get("resolved_count", 0)
        }
