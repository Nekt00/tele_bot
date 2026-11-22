from typing import Optional, Dict, Any
from sqlalchemy.ext.asyncio import AsyncSession

from app.enums import QuizStep
from .base import BaseService
from .session_service import SessionService


class FSMService(BaseService):
    """Сервис для управления конечным автоматом опроса"""
    
    def __init__(self, session: AsyncSession):
        super().__init__(session)
        self.session_service = SessionService(session)
    
    async def next_step(
        self,
        user_id: int,
        answer: Optional[str] = None,
        answer_key: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Перейти к следующему шагу
        """
        # Получаем текущую сессию
        session_data = await self.session_service.get_session_data(user_id)
        
        if not session_data:
            return {
                "success": False,
                "error": "Сессия не найдена",
                "step": QuizStep.ROUTER.value
            }
        
        current_step = await self.session_service.get_current_step(user_id)
        
        # Сохраняем ответ если он есть
        if answer and answer_key:
            if "data" not in session_data:
                session_data["data"] = {}
            session_data["data"][answer_key] = answer
            await self.session_service.update_session_data(user_id, session_data)
        
        # Проверяем, не последний ли шаг
        if QuizStep.is_last_step(current_step):
            return {
                "success": True,
                "is_finished": True,
                "step": current_step,
                "message": "Опрос завершён"
            }
        
        # Переходим к следующему шагу
        next_step = QuizStep.get_next_step(current_step)
        await self.session_service.update_session_step(user_id, next_step)
        
        # Получаем информацию о следующем шаге
        step_info = QuizStep.get_step_info(next_step)
        
        return {
            "success": True,
            "is_finished": False,
            "step": next_step,
            "step_info": step_info,
            "current_data": session_data.get("data", {})
        }
    
    async def previous_step(self, user_id: int) -> Dict[str, Any]:
        """
        Вернуться к предыдущему шагу
        """
        current_step = await self.session_service.get_current_step(user_id)
        
        if QuizStep.is_first_step(current_step):
            return {
                "success": False,
                "error": "Это первый шаг, нельзя вернуться назад",
                "step": current_step
            }
        
        previous_step = QuizStep.get_previous_step(current_step)
        await self.session_service.update_session_step(user_id, previous_step)
        
        step_info = QuizStep.get_step_info(previous_step)
        
        return {
            "success": True,
            "step": previous_step,
            "step_info": step_info
        }
    
    async def resume(self, user_id: int) -> Dict[str, Any]:
        """
        Возобновить опрос с текущего шага
        """
        current_step = await self.session_service.get_current_step(user_id)
        session_data = await self.session_service.get_session_data(user_id)
        
        if not session_data:
            return {
                "success": False,
                "error": "Сессия не найдена",
                "step": QuizStep.ROUTER.value
            }
        
        step_info = QuizStep.get_step_info(current_step)
        
        return {
            "success": True,
            "step": current_step,
            "step_info": step_info,
            "current_data": session_data.get("data", {})
        }
    
    async def finish(self, user_id: int, final_answer: Optional[str] = None) -> Dict[str, Any]:
        """
        Завершить опрос
        """
        session_data = await self.session_service.get_session_data(user_id)
        
        if not session_data:
            return {
                "success": False,
                "error": "Сессия не найдена"
            }
        
        # Сохраняем финальный ответ если он есть
        if final_answer and "data" in session_data:
            session_data["data"]["problem_description"] = final_answer
            await self.session_service.update_session_data(user_id, session_data)
        
        return {
            "success": True,
            "data": session_data.get("data", {}),
            "group_chat_id": session_data.get("group_chat_id"),
            "username": session_data.get("username"),
            "first_name": session_data.get("first_name")
        }
    
    async def process_answer(
        self,
        user_id: int,
        step: int,
        answer: str,
        is_custom: bool = False
    ) -> Dict[str, Any]:
        """
        Обработать ответ на текущем шаге
        """
        step_info = QuizStep.get_step_info(step)
        answer_key = step_info.get("name")
        
        if not answer_key:
            return {
                "success": False,
                "error": "Неизвестный шаг"
            }
        
        # Сохраняем ответ
        session_data = await self.session_service.get_session_data(user_id)
        
        if not session_data:
            return {
                "success": False,
                "error": "Сессия не найдена"
            }
        
        if "data" not in session_data:
            session_data["data"] = {}
        
        session_data["data"][answer_key] = answer
        await self.session_service.update_session_data(user_id, session_data)
        
        # Если это последний шаг - завершаем
        if QuizStep.is_last_step(step):
            return await self.finish(user_id)
        
        # Переходим к следующему шагу
        return await self.next_step(user_id)
    
    async def get_current_step_info(self, user_id: int) -> Dict[str, Any]:
        """
        Получить информацию о текущем шаге
        """
        current_step = await self.session_service.get_current_step(user_id)
        step_info = QuizStep.get_step_info(current_step)
        session_data = await self.session_service.get_session_data(user_id)
        
        return {
            "step": current_step,
            "step_info": step_info,
            "current_data": session_data.get("data", {}) if session_data else {}
        }
    
    async def is_quiz_active(self, user_id: int) -> bool:
        """
        Проверить, активен ли опрос
        """
        return await self.session_service.has_active_quiz(user_id)
    
    async def reset(self, user_id: int) -> None:
        """
        Сбросить опрос
        """
        await self.session_service.clear_session(user_id)
