from typing import Optional, Dict, Any, List
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import TicketRepository
from .base import BaseService


class TicketService(BaseService):
    """Сервис для управления обращениями"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.ticket_repo = TicketRepository(session)
    
    async def create_free_ticket(
        self,
        user_id: int,
        group_chat_id: int,
        description: str,
        username: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Создать обращение из свободного описания
        """
        ticket = await self.ticket_repo.create_free_ticket(
            user_id=user_id,
            group_chat_id=group_chat_id,
            description=description,
            username=username
        )
        
        return {
            "success": True,
            "ticket_id": ticket.id,
            "created_at": ticket.created_at
        }
    
    async def get_user_tickets(self, user_id: int, limit: int = 10) -> List[Dict[str, Any]]:
        """
        Получить обращения пользователя
        """
        tickets = await self.ticket_repo.get_by_user(user_id, limit)
        
        return [
            {
                "id": t.id,
                "type": t.ticket_type,
                "status": t.status,
                "created_at": t.created_at,
                "problem": t.problem_description[:100] if t.problem_description else "Нет описания"
            }
            for t in tickets
        ]
    
    async def get_group_tickets(
        self, 
        group_chat_id: int, 
        limit: int = 50,
        status: Optional[str] = None
    ) -> List[Dict[str, Any]]:
        """
        Получить обращения группы
        """
        tickets = await self.ticket_repo.get_by_group(group_chat_id, limit)
        
        if status:
            tickets = [t for t in tickets if t.status == status]
        
        return [
            {
                "id": t.id,
                "user_id": t.user_id,
                "username": t.username,
                "type": t.ticket_type,
                "status": t.status,
                "created_at": t.created_at,
                "problem": t.problem_description[:100] if t.problem_description else "Нет описания"
            }
            for t in tickets
        ]
    
    async def update_ticket_status(self, ticket_id: int, status: str) -> Dict[str, Any]:
        """
        Обновить статус обращения
        """
        ticket = await self.ticket_repo.update_status(ticket_id, status)
        
        if not ticket:
            return {"error": "Обращение не найдено"}
        
        return {
            "success": True,
            "ticket_id": ticket.id,
            "status": ticket.status
        }
    
    async def get_recent_tickets(
        self, 
        group_chat_id: Optional[int] = None, 
        limit: int = 10
    ) -> List[Dict[str, Any]]:
        """
        Получить последние обращения
        """
        tickets = await self.ticket_repo.get_recent(group_chat_id, limit)
        
        return [
            {
                "id": t.id,
                "user_id": t.user_id,
                "username": t.username or f"user_{t.user_id}",
                "type": "📋 Опрос" if t.ticket_type == "quiz" else "✏️ Свободное описание",
                "status": t.status,
                "created_at": t.created_at.strftime("%Y-%m-%d %H:%M")
            }
            for t in tickets
        ]