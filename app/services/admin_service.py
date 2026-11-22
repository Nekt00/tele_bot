from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession
from telegram.ext import ContextTypes
from datetime import datetime

from app.repositories import TicketRepository, GroupRepository
from .base import BaseService
from .statistics_service import StatisticsService
from .ticket_service import TicketService


class AdminService(BaseService):
    """Сервис для административных функций"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.ticket_repo = TicketRepository(session)
        self.group_repo = GroupRepository(session)
        self.stats_service = StatisticsService(session)
        self.ticket_service = TicketService(session)
    
    async def is_admin(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        chat_id: int,
        user_id: int
    ) -> bool:
        """
        Проверить, является ли пользователь администратором группы
        """
        try:
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_ids = [admin.user.id for admin in admins if not admin.user.is_bot]
            return user_id in admin_ids
        except Exception as e:
            print(f"Ошибка проверки прав администратора: {e}")
            return False
    
    async def get_user_admin_groups(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получить список групп, где пользователь является администратором
        """
        admin_groups = []
        bot_groups = context.bot_data.get("bot_groups", {})
        
        for chat_id, group_info in bot_groups.items():
            if await self.is_admin(context, chat_id, user_id):
                admin_groups.append({
                    'chat_id': chat_id,
                    'title': group_info.get('title', f'Группа {chat_id}')
                })
        
        return admin_groups
    
    async def get_admin_panel_data(self, group_chat_id: int) -> Dict[str, Any]:
        """
        Получить данные для админ-панели
        """
        # Получаем статистику
        stats = await self.stats_service.get_group_stats(group_chat_id)
        
        # Получаем последние обращения
        recent_tickets = await self.ticket_service.get_recent_tickets(group_chat_id, limit=10)
        
        # Получаем распределение по статусам
        status_distribution = await self.stats_service.get_status_distribution(group_chat_id)
        
        # Получаем информацию о группе
        group = await self.group_repo.get_by_chat_id(group_chat_id)
        
        return {
            "group_title": group.title if group else "Неизвестная группа",
            "group_chat_id": group_chat_id,
            "stats": stats,
            "recent_tickets": recent_tickets,
            "status_distribution": status_distribution,
            "last_updated": datetime.now()
        }
    
    async def get_admins_list(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        group_chat_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получить список администраторов группы
        """
        try:
            admins = await context.bot.get_chat_administrators(group_chat_id)
            
            admin_list = []
            for admin in admins:
                if not admin.user.is_bot:
                    admin_list.append({
                        "user_id": admin.user.id,
                        "full_name": admin.user.full_name,
                        "username": admin.user.username,
                        "is_creator": admin.user.id == admins[0].user.id if admins else False
                    })
            
            return admin_list
        except Exception as e:
            print(f"Ошибка получения списка администраторов: {e}")
            return []
    
    async def get_all_groups_stats(self) -> Dict[str, Any]:
        """
        Получить статистику по всем группам
        """
        groups = await self.group_repo.get_active_groups()
        
        all_stats = []
        total_tickets = 0
        
        for group in groups:
            stats = await self.stats_service.get_group_stats(group.chat_id)
            all_stats.append({
                "group_title": group.title,
                "group_chat_id": group.chat_id,
                "stats": stats
            })
            total_tickets += stats.get("total", 0)
        
        return {
            "total_groups": len(groups),
            "total_tickets": total_tickets,
            "groups": all_stats,
            "last_updated": datetime.now()
        }
    
    async def format_stats_message(self, group_chat_id: int) -> str:
        """
        Форматировать сообщение со статистикой для отправки
        """
        stats = await self.stats_service.get_group_stats(group_chat_id)
        
        message = f"""
📊 Статистика группы: {stats.get('group_title', 'Неизвестная группа')}

📋 Всего обращений: {stats.get('total', 0)}
🆕 За сегодня: {stats.get('today', 0)}
📅 За неделю: {stats.get('week', 0)}

👥 Уникальные пользователи: {stats.get('unique_users', 0)}

🏷️ По типу:
• Опрос: {stats.get('quiz_count', 0)}
• Свободное описание: {stats.get('free_count', 0)}

📌 По статусу:
• Новые: {stats.get('new_count', 0)}
• В обработке: {stats.get('in_progress_count', 0)}
• Решены: {stats.get('resolved_count', 0)}

🕐 Обновлено: {datetime.now().strftime('%d.%m.%Y %H:%M:%S')}
        """
        
        return message.strip()
    
    async def format_admins_message(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        group_chat_id: int,
        group_title: str
    ) -> str:
        """
        Форматировать сообщение со списком администраторов
        """
        admins = await self.get_admins_list(context, group_chat_id)
        
        if not admins:
            return "❌ Не удалось получить список администраторов"
        
        admin_lines = []
        for admin in admins:
            admin_text = f"• {admin['full_name']}"
            if admin['username']:
                admin_text += f" (@{admin['username']})"
            if admin['is_creator']:
                admin_text += " 👑"
            admin_lines.append(admin_text)
        
        message = f"👥 Администраторы группы: {group_title}\n\n" + "\n".join(admin_lines)
        
        return message
    
    async def format_recent_tickets_message(
        self,
        group_chat_id: int,
        limit: int = 10
    ) -> str:
        """
        Форматировать сообщение с последними обращениями
        """
        tickets = await self.ticket_service.get_recent_tickets(group_chat_id, limit)
        
        if not tickets:
            return "📭 Пока нет ни одного обращения."
        
        lines = ["📋 Последние обращения:\n"]
        for ticket in tickets:
            lines.append(
                f"• {ticket['created_at']} | {ticket['username']} | {ticket['type']}"
            )
        
        return "\n".join(lines)
    
    async def can_access_group(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int,
        group_chat_id: int
    ) -> bool:
        """
        Проверить, имеет ли пользователь доступ к управлению группой
        """
        admin_groups = await self.get_user_admin_groups(context, user_id)
        return any(g['chat_id'] == group_chat_id for g in admin_groups)
    
    async def get_accessible_groups(
        self,
        context: ContextTypes.DEFAULT_TYPE,
        user_id: int
    ) -> List[Dict[str, Any]]:
        """
        Получить группы, доступные для управления пользователю
        """
        return await self.get_user_admin_groups(context, user_id)