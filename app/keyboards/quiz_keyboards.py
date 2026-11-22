from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from app.config import settings
from app.utils.deep_links import create_quiz_payload

def get_firmware_keyboard():
    keyboard = [
        [InlineKeyboardButton("Штатная (stock)", callback_data="firmware_stock")],
        [InlineKeyboardButton("Модифицированная", callback_data="firmware_modified")],
        [InlineKeyboardButton("◀️ Назад", callback_data="quiz_back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_protocol_keyboard():
    keyboard = [
        [InlineKeyboardButton("👽 VLESS", callback_data="protocol_vless")],
        [InlineKeyboardButton("👾 xVLESS", callback_data="protocol_xvless")],
        [InlineKeyboardButton("🦄 Trojan", callback_data="protocol_trojan")],
        [InlineKeyboardButton("🐉 WireGuard", callback_data="protocol_wireguard")],
        [InlineKeyboardButton("🔁 Другой", callback_data="protocol_other")],
        [InlineKeyboardButton("◀️ Назад", callback_data="quiz_back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_os_keyboard():
    keyboard = [
        [InlineKeyboardButton("🖥 Windows", callback_data="os_windows")],
        [InlineKeyboardButton("🍏 macOS", callback_data="os_macos")],
        [InlineKeyboardButton("🐧 Linux", callback_data="os_linux")],
        [InlineKeyboardButton("📱 Android", callback_data="os_android")],
        [InlineKeyboardButton("📱 iOS", callback_data="os_ios")],
        [InlineKeyboardButton("🔄 Другая", callback_data="os_other")],
        [InlineKeyboardButton("◀️ Назад", callback_data="quiz_back")],
    ]
    return InlineKeyboardMarkup(keyboard)

def get_main_keyboard(user_id: int, chat_id: int, bot_username: str):
    bot_username = bot_username.lstrip("@")
    payload = create_quiz_payload(user_id, chat_id, settings.TOKEN)
    quiz_url = f"https://t.me/{bot_username}?start={payload}"
    keyboard = [
        [InlineKeyboardButton("🔢 Пройти опрос", url=quiz_url)],
        [InlineKeyboardButton("📝 Описать проблему самому", callback_data=f"free_{user_id}_{chat_id}")]
    ]
    return InlineKeyboardMarkup(keyboard)
