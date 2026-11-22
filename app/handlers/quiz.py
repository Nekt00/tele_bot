from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.enums import QuizStep
from app.keyboards.quiz_keyboards import (
    get_firmware_keyboard,
    get_os_keyboard,
    get_protocol_keyboard,
)

user_sessions = {}

FIRMWARE_OPTIONS = {
    "stock": "Штатная",
    "modified": "Модифицированная"
}

PROTOCOL_OPTIONS = {
    "vless": "VLESS",
    "xvless": "xVLESS",
    "trojan": "Trojan",
    "wireguard": "WireGuard",
    "other": "Другая"
}

OS_OPTIONS = {
    "windows": "Windows",
    "macos": "macOS",
    "linux": "Linux",
    "android": "Android",
    "ios": "iOS",
    "other": "Другая"
}


def get_back_button():
    """Только кнопка Назад для текстовых вопросов"""
    return InlineKeyboardMarkup([[InlineKeyboardButton("◀️ Назад", callback_data="quiz_back")]])


async def ask_question(context: ContextTypes.DEFAULT_TYPE, user_id: int, step: int) -> int:
    """Задать вопрос в зависимости от шага"""
    
    if step == QuizStep.ROUTER.value:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="1⃣ Вопрос 1 из 5:\n\nВведите модель вашего роутера\n(например, Keenetic Giga, Xiaomi AX3000)",
            reply_markup=get_back_button()
        )
    
    elif step == QuizStep.FIRMWARE.value:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="2⃣ Вопрос 2 из 5:\n\nКакая прошивка установлена?",
            reply_markup=get_firmware_keyboard()
        )
    
    elif step == QuizStep.PROTOCOL.value:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="3⃣ Вопрос 3 из 5:\n\nКакой протокол используете?",
            reply_markup=get_protocol_keyboard()
        )
    
    elif step == QuizStep.OS.value:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="4⃣ Вопрос 4 из 5:\n\nКакая у вас операционная система?",
            reply_markup=get_os_keyboard()
        )
    
    elif step == QuizStep.DESCRIPTION.value:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="5⃣ Вопрос 5 из 5:\n\nОпишите проблему своими словами:\n• Что происходит?\n• Когда появилась?\n• Как часто?",
            reply_markup=get_back_button()
        )
    
    else:
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="❌ Что-то пошло не так. Начните опрос заново."
        )
    
    return msg.message_id
