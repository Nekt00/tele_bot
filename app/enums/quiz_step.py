from enum import Enum
from typing import Dict, Any


class QuizStep(Enum):
    """Шаги опроса пользователя"""
    ROUTER = 0      # Модель роутера
    FIRMWARE = 1    # Прошивка
    PROTOCOL = 2    # Протокол
    OS = 3          # Операционная система
    DESCRIPTION = 4 # Описание проблемы
    
    @classmethod
    def get_step_info(cls, step: int) -> Dict[str, Any]:
        """Получить информацию о шаге"""
        steps = {
            0: {
                "name": "router_model",
                "question": "Введите модель вашего роутера",
                "type": "text",
                "example": "(например, Keenetic Giga, Xiaomi AX3000, ASUS RT-AC68U)"
            },
            1: {
                "name": "firmware",
                "question": "Какая прошивка установлена?",
                "type": "buttons",
                "options": ["Штатная (stock)", "Модифицированная"]
            },
            2: {
                "name": "protocol",
                "question": "Какой протокол используете?",
                "type": "buttons",
                "options": ["VLESS", "xVLESS", "Trojan", "WireGuard", "Другая"]
            },
            3: {
                "name": "os",
                "question": "Какая у вас операционная система?",
                "type": "buttons",
                "options": ["Windows", "macOS", "Linux", "Android", "iOS", "Другая"]
            },
            4: {
                "name": "problem_description",
                "question": "Опишите проблему своими словами",
                "type": "text",
                "example": "Что именно происходит? Когда появилась проблема? Как часто повторяется?"
            }
        }
        return steps.get(step, {})
    
    @classmethod
    def get_next_step(cls, current_step: int) -> int:
        """Получить следующий шаг"""
        return current_step + 1 if current_step < 4 else 4
    
    @classmethod
    def get_previous_step(cls, current_step: int) -> int:
        """Получить предыдущий шаг"""
        return current_step - 1 if current_step > 0 else 0
    
    @classmethod
    def is_last_step(cls, step: int) -> bool:
        """Проверить, является ли шаг последним"""
        return step == cls.DESCRIPTION.value
    
    @classmethod
    def is_first_step(cls, step: int) -> bool:
        """Проверить, является ли шаг первым"""
        return step == cls.ROUTER.value
