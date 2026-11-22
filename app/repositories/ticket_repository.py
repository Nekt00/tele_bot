from typing import Optional, List, Dict, Any
from datetime import datetime, timedelta
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select, func, and_

from app.models import Ticket
from .base import BaseRepository


class TicketRepository(BaseRepository[Ticket]):
    """Репозиторий для работы с обращениями"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(Ticket, session)
    
    async def create_quiz_ticket(
        self,
        user_id: int,
        group_chat_id: int,
        answers: Dict[str, Any],
        username: Optional[str] = None
    ) -> Ticket:
        return await self.create(
            user_id=user_id,
            username=username,
            group_chat_id=group_chat_id,
            router_model=answers.get("router_model"),
            firmware=answers.get("firmware"),
            protocol=answers.get("protocol"),
            os=answers.get("os"),
            problem_description=answers.get("problem_description"),
            extra_data=answers,
            ticket_type="quiz",
            status="new"
        )
    
    async def create_free_ticket(
        self,
        user_id: int,
        group_chat_id: int,
        description: str,
        username: Optional[str] = None
    ) -> Ticket:
        return await self.create(
            user_id=user_id,
            username=username,
            group_chat_id=group_chat_id,
            problem_description=description,
            extra_data={"description": description},
            ticket_type="free",
            status="new"
        )
    
    async def get_by_user(self, user_id: int, limit: int = 10) -> List[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.user_id == user_id)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_by_group(self, group_chat_id: int, limit: int = 50) -> List[Ticket]:
        result = await self.session.execute(
            select(Ticket)
            .where(Ticket.group_chat_id == group_chat_id)
            .order_by(Ticket.created_at.desc(), Ticket.id.desc())
            .limit(limit)
        )
        return list(result.scalars().all())
    
    async def get_stats(
        self, 
        group_chat_id: Optional[int] = None,
        start_date: Optional[datetime] = None,
        end_date: Optional[datetime] = None
    ) -> Dict[str, Any]:
        """Получить статистику по обращениям"""
        
        # Базовый фильтр
        filters = []
        if group_chat_id:
            filters.append(Ticket.group_chat_id == group_chat_id)
        if start_date:
            filters.append(Ticket.created_at >= start_date)
        if end_date:
            filters.append(Ticket.created_at < end_date)
        
        # Общее количество
        total_query = select(func.count()).select_from(Ticket)
        if filters:
            total_query = total_query.where(and_(*filters))
        total = await self.session.scalar(total_query)
        
        # За сегодня
        today = datetime.now().date()
        today_start = datetime(today.year, today.month, today.day)
        today_filters = filters + [Ticket.created_at >= today_start]
        today_query = select(func.count()).select_from(Ticket).where(and_(*today_filters))
        today_count = await self.session.scalar(today_query)
        
        # За неделю
        week_ago = datetime.now() - timedelta(days=7)
        week_filters = filters + [Ticket.created_at >= week_ago]
        week_query = select(func.count()).select_from(Ticket).where(and_(*week_filters))
        week_count = await self.session.scalar(week_query)
        
        # По типам
        quiz_filters = filters + [Ticket.ticket_type == "quiz"]
        quiz_query = select(func.count()).select_from(Ticket).where(and_(*quiz_filters))
        quiz_count = await self.session.scalar(quiz_query)
        
        free_filters = filters + [Ticket.ticket_type == "free"]
        free_query = select(func.count()).select_from(Ticket).where(and_(*free_filters))
        free_count = await self.session.scalar(free_query)
        
        # По статусам
        new_filters = filters + [Ticket.status == "new"]
        new_query = select(func.count()).select_from(Ticket).where(and_(*new_filters))
        new_count = await self.session.scalar(new_query)
        
        in_progress_filters = filters + [Ticket.status == "in_progress"]
        in_progress_query = select(func.count()).select_from(Ticket).where(and_(*in_progress_filters))
        in_progress_count = await self.session.scalar(in_progress_query)
        
        resolved_filters = filters + [Ticket.status == "resolved"]
        resolved_query = select(func.count()).select_from(Ticket).where(and_(*resolved_filters))
        resolved_count = await self.session.scalar(resolved_query)
        
        # Уникальные пользователи
        unique_query = select(func.count(func.distinct(Ticket.user_id))).select_from(Ticket)
        if filters:
            unique_query = unique_query.where(and_(*filters))
        unique_users = await self.session.scalar(unique_query)
        
        return {
            "total": total or 0,
            "today": today_count or 0,
            "week": week_count or 0,
            "quiz_count": quiz_count or 0,
            "free_count": free_count or 0,
            "new_count": new_count or 0,
            "in_progress_count": in_progress_count or 0,
            "resolved_count": resolved_count or 0,
            "unique_users": unique_users or 0,
        }
    
    async def get_recent(self, group_chat_id: Optional[int] = None, limit: int = 10) -> List[Ticket]:
        query = select(Ticket).order_by(Ticket.created_at.desc(), Ticket.id.desc())
        
        if group_chat_id:
            query = query.where(Ticket.group_chat_id == group_chat_id)
        
        query = query.limit(limit)
        result = await self.session.execute(query)
        return list(result.scalars().all())
    
    async def update_status(self, ticket_id: int, status: str) -> Optional[Ticket]:
        ticket = await self.get(id=ticket_id)
        if ticket:
            ticket.status = status
            await self.session.flush()
        return ticket
