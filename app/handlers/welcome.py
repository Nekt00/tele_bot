import asyncio
from telegram import Update
from telegram.ext import ContextTypes
from app.keyboards.quiz_keyboards import get_main_keyboard
from app.utils.logger import bot_logger
from app.database import session_scope
from app.repositories import GroupRepository
from app.models import PendingWelcome


PENDING_WELCOME_USERS_KEY = "pending_welcome_users"


def mark_user_awaiting_choice(context, chat_id: int, user_id: int) -> None:
    pending_users = context.bot_data.setdefault(PENDING_WELCOME_USERS_KEY, set())
    pending_users.add((chat_id, user_id))


def is_user_awaiting_choice(context, chat_id: int, user_id: int) -> bool:
    pending_users = context.bot_data.get(PENDING_WELCOME_USERS_KEY, set())
    return (chat_id, user_id) in pending_users


def clear_user_awaiting_choice(context, chat_id: int, user_id: int) -> bool:
    pending_users = context.bot_data.get(PENDING_WELCOME_USERS_KEY, set())
    key = (chat_id, user_id)
    if key not in pending_users:
        return False
    pending_users.remove(key)
    return True


async def save_pending_welcome(chat_id: int, user_id: int) -> None:
    try:
        async with session_scope() as session:
            if await session.get(PendingWelcome, (chat_id, user_id)) is None:
                session.add(PendingWelcome(chat_id=chat_id, user_id=user_id))
    except Exception as exc:
        bot_logger.exception("Ошибка сохранения ожидающего приветствия: %s", exc)


async def delete_pending_welcome(chat_id: int, user_id: int) -> None:
    try:
        async with session_scope() as session:
            pending = await session.get(PendingWelcome, (chat_id, user_id))
            if pending is not None:
                await session.delete(pending)
    except Exception as exc:
        bot_logger.exception("Ошибка удаления ожидающего приветствия: %s", exc)


async def send_with_retry(context, chat_id, text, reply_markup=None, max_retries=3):
    """Отправка сообщения с повторными попытками"""
    for attempt in range(max_retries):
        try:
            await context.bot.send_message(
                chat_id=chat_id,
                text=text,
                reply_markup=reply_markup,
                connect_timeout=30,
                read_timeout=30,
                write_timeout=30
            )
            return True
        except Exception as e:
            bot_logger.warning(f"Попытка {attempt + 1}/{max_retries} не удалась: {e}")
            if attempt < max_retries - 1:
                await asyncio.sleep(2 ** attempt)  # экспоненциальная задержка
            else:
                bot_logger.error(f"Не удалось отправить сообщение после {max_retries} попыток: {e}")
                return False
    return False


async def greet_new_member(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Приветствие нового участника"""
    if not update.message.chat.type in ["group", "supergroup"]:
        return
    
    new_members = update.message.new_chat_members
    if not new_members:
        return

    chat_id = update.message.chat_id
    chat_title = update.message.chat.title
    
    for member in new_members:
        # Если это бот - сохраняем группу в БД
        if member.id == context.bot.id:
            bot_logger.info(f"✅ Бот добавлен в группу: {chat_title} (ID: {chat_id})")
            
            # Сохраняем в БД
            try:
                async with session_scope() as session:
                    repo = GroupRepository(session)
                    await repo.create_or_update(chat_id=chat_id, title=chat_title)
            except Exception as e:
                bot_logger.exception("Ошибка сохранения группы в БД: %s", e)
                return
            
            # Сохраняем в bot_data
            if "bot_groups" not in context.bot_data:
                context.bot_data["bot_groups"] = {}
            context.bot_data["bot_groups"][chat_id] = {'title': chat_title}
            
            return
        
        # Обычный пользователь - отправляем приветствие
        try:
            # Небольшая задержка перед отправкой
            await asyncio.sleep(2)
            
            welcome_text = (
                f"Привет, {member.first_name}! 👋\n\n"
                f"Добро пожаловать в группу \"{chat_title}\"!\n\n"
                f"Как хочешь оформить обращение?\n\n"
                f"🔹 Пройти опрос - я задам вопросы в личке\n"
                f"🔴 Описать проблему самому\n\n"
                f"Выбери вариант:"
            )
            
            sent = await send_with_retry(
                context,
                chat_id,
                welcome_text,
                get_main_keyboard(member.id, chat_id, context.bot.username)
            )
            if sent:
                mark_user_awaiting_choice(context, chat_id, member.id)
                await save_pending_welcome(chat_id, member.id)
        except Exception as e:
            bot_logger.error(f"Ошибка отправки приветствия пользователю {member.id}: {e}")
