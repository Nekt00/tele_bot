from typing import Dict, Any, Optional
from datetime import datetime
from sqlalchemy.ext.asyncio import AsyncSession

from app.repositories import TicketRepository
from .base import BaseService
from .session_service import SessionService


class QuizService(BaseService):
    """Сервис для управления опросами"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.ticket_repo = TicketRepository(session)
        self.session_service = SessionService(session)
    
    async def process_quiz_answer(
        self, 
        user_id: int, 
        step: int, 
        answer: str
    ) -> Dict[str, Any]:
        """
        Обработать ответ на вопрос опроса
        """
        session_data = await self.session_service.get_session_data(user_id)
        
        if not session_data:
            return {"error": "Сессия не найдена"}
        
        if "data" not in session_data:
            session_data["data"] = {}
        
        # Сохраняем ответ в зависимости от шага
        if step == 0:
            session_data["data"]["router_model"] = answer
            next_step = 1
            message = f"✅ Модель сохранена: {answer}"
        elif step == 1:
            session_data["data"]["firmware"] = answer
            next_step = 2
            message = f"✅ Выбрана прошивка: {answer}"
        elif step == 2:
            session_data["data"]["protocol"] = answer
            next_step = 3
            message = f"✅ Выбран протокол: {answer}"
        elif step == 3:
            session_data["data"]["os"] = answer
            next_step = 4
            message = f"✅ Выбрана ОС: {answer}"
        else:
            return {"error": "Неверный шаг опроса"}
        
        # Обновляем сессию
        await self.session_service.update_session_data(user_id, session_data)
        await self.session_service.update_session_step(user_id, next_step)
        
        return {
            "success": True,
            "next_step": next_step,
            "message": message,
            "data": session_data["data"]
        }
    
    async def finish_quiz(
        self,
        user_id: int,
        problem_description: str
    ) -> Dict[str, Any]:
        """
        Завершить опрос и сохранить результат
        """
        session_data = await self.session_service.get_session_data(user_id)
        
        if not session_data:
            return {"error": "Сессия не найдена"}
        
        # Добавляем описание проблемы
        session_data["data"]["problem_description"] = problem_description
        
        # Сохраняем обращение
        ticket = await self.ticket_repo.create_quiz_ticket(
            user_id=user_id,
            group_chat_id=session_data.get("group_chat_id"),
            answers=session_data["data"],
            username=session_data.get("username")
        )
        
        # Очищаем сессию
        await self.session_service.clear_session(user_id)
        
        return {
            "success": True,
            "ticket_id": ticket.id,
            "data": session_data["data"],
            "created_at": ticket.created_at
        }
    
    async def get_next_question(self, current_step: int) -> Dict[str, Any]:
        """
        Получить следующий вопрос опроса
        """
        questions = {
            0: {
                "step": 0,
                "question": "Введите модель вашего роутера",
                "type": "text",
                "example": "(например, Keenetic Giga, Xiaomi AX3000, ASUS RT-AC68U)"
            },
            1: {
                "step": 1,
                "question": "Какая прошивка установлена?",
                "type": "buttons",
                "options": ["Штатная (stock)", "Модифицированная"]
            },
            2: {
                "step": 2,
                "question": "Какой протокол используете?",
                "type": "buttons",
                "options": ["VLESS", "xVLESS", "Trojan", "WireGuard", "Другая"]
            },
            3: {
                "step": 3,
                "question": "Какая у вас операционная система?",
                "type": "buttons",
                "options": ["Windows", "macOS", "Linux", "Android", "iOS", "Другая"]
            },
            4: {
                "step": 4,
                "question": "Опишите проблему своими словами",
                "type": "text",
                "example": "Что именно происходит? Когда появилась проблема? Как часто повторяется?"
            }
        }
        
        return questions.get(current_step, {"error": "Опрос завершён"})