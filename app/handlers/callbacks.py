import asyncio
from copy import deepcopy
from telegram import Update
from telegram.ext import ContextTypes
from app.config import settings
from app.handlers.quiz import user_sessions, ask_question
from app.enums import QuizStep
from app.database import session_scope
from app.services import SessionService
from app.utils.logger import bot_logger
from app.handlers.free_mode import send_free_description_instruction
from app.handlers.welcome import clear_user_awaiting_choice, delete_pending_welcome


async def save_session_to_db(user_id: int, session_data: dict) -> bool:
    """Сохраняет сессию в БД"""
    try:
        async with session_scope() as session:
            session_service = SessionService(session)
            await session_service.get_or_create_session(
                user_id=user_id,
                mode=session_data.get("mode", "quiz"),
                group_chat_id=session_data.get("group_chat_id"),
                first_name=session_data.get("first_name"),
                username=session_data.get("username")
            )
            await session_service.update_session_step(user_id, session_data.get("step", 0))
            await session_service.update_session_data(user_id, session_data)
        return True
    except Exception as e:
        bot_logger.exception("Ошибка сохранения сессии в БД: %s", e)
        return False


async def start_quiz_session(
    user_id: int,
    group_chat_id: int,
    first_name: str,
    username: str,
) -> dict:
    session_data = {
        "mode": "quiz",
        "step": QuizStep.ROUTER.value,
        "group_chat_id": group_chat_id,
        "first_name": first_name,
        "username": username,
        "data": {},
        "last_question_id": None,
    }
    if not await save_session_to_db(user_id, session_data):
        raise RuntimeError("Не удалось сохранить сессию опроса")
    user_sessions[user_id] = session_data
    return session_data


def parse_target_callback(data: str) -> tuple[int, int] | None:
    parts = data.split('_')
    if len(parts) != 3:
        return None

    _, target_user_id, group_chat_id = parts
    try:
        return int(target_user_id), int(group_chat_id)
    except ValueError:
        return None


async def delete_message_safely(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def persist_transition(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    previous_session: dict,
) -> bool:
    if await save_session_to_db(user_id, user_sessions[user_id]):
        return True
    user_sessions[user_id] = previous_session
    await context.bot.send_message(
        chat_id=user_id,
        text="❌ Не удалось сохранить ответ. Попробуйте ещё раз позже.",
    )
    return False


async def button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок выбора опроса"""
    query = update.callback_query
    await query.answer()
    
    data = query.data
    user_id = query.from_user.id
    first_name = query.from_user.first_name
    username = query.from_user.username or "нет username"
    chat_id = query.message.chat_id
    
    if data.startswith('quiz_'):
        callback_target = parse_target_callback(data)
        if callback_target is None:
            await context.bot.send_message(chat_id=chat_id, text="❌ Ошибка формата кнопки")
            return
        target_user_id, group_chat_id = callback_target
        
        if target_user_id != user_id:
            await context.bot.send_message(chat_id=chat_id, text="Эта кнопка не для Вас!")
            return

        if group_chat_id != chat_id:
            await context.bot.send_message(chat_id=chat_id, text="❌ Кнопка относится к другой группе")
            return

        active_session = user_sessions.get(user_id)
        if active_session:
            await context.bot.send_message(
                chat_id=chat_id,
                text="ℹ️ У вас уже есть активное обращение. Завершите его перед созданием нового.",
            )
            return

        try:
            await start_quiz_session(
                user_id=user_id,
                group_chat_id=group_chat_id,
                first_name=first_name,
                username=username,
            )
        except RuntimeError:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Не удалось начать опрос. Попробуйте ещё раз позже.",
            )
            return

        await delete_message_safely(context, chat_id, query.message.message_id)
        clear_user_awaiting_choice(context, group_chat_id, user_id)
        await delete_pending_welcome(group_chat_id, user_id)
        
        # Отправляем сообщение с инструкцией
        msg = await context.bot.send_message(
            chat_id=chat_id,
            text=f"{first_name}, напиши мне /start в личные сообщения, чтобы начать опрос.\n\n"
                 f"👤 Мой username: @{context.bot.username}"
        )
        
        async def delete_delayed():
            await asyncio.sleep(settings.DELETE_DELAYS["group_instruction"])
            try:
                await context.bot.delete_message(chat_id=chat_id, message_id=msg.message_id)
            except:
                pass
        
        asyncio.create_task(delete_delayed())
    
    elif data.startswith("free_"):
        callback_target = parse_target_callback(data)
        if callback_target is None:
            await context.bot.send_message(chat_id=chat_id, text="❌ Ошибка формата кнопки")
            return
        target_user_id, group_chat_id = callback_target
        
        if target_user_id != user_id:
            await context.bot.send_message(chat_id=chat_id, text="Эта кнопка не для Вас")
            return

        if group_chat_id != chat_id:
            await context.bot.send_message(chat_id=chat_id, text="❌ Кнопка относится к другой группе")
            return


        active_session = user_sessions.get(user_id)
        if active_session:
            active_group_id = active_session.get("group_chat_id")
            if active_group_id != group_chat_id:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="❌ Сначала завершите активное обращение для другой группы.",
                )
            else:
                await context.bot.send_message(
                    chat_id=chat_id,
                    text="ℹ️ У вас уже есть активное обращение. Завершите его перед созданием нового.",
                )
            return

        # Свободное описание
        sent_msg = await send_free_description_instruction(
            context,
            group_chat_id,
            first_name,
        )
        
        session_data = {
            "mode": "free",
            "instruction_msg_id": sent_msg.message_id,
            "group_chat_id": group_chat_id,
            "first_name": first_name
        }
        if await save_session_to_db(user_id, session_data):
            user_sessions[user_id] = session_data
            await delete_message_safely(context, chat_id, query.message.message_id)
            clear_user_awaiting_choice(context, group_chat_id, user_id)
            await delete_pending_welcome(group_chat_id, user_id)
        else:
            await context.bot.send_message(
                chat_id=chat_id,
                text="❌ Не удалось начать обращение. Попробуйте ещё раз позже.",
            )


async def quiz_button_callback(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Обработка кнопок внутри опроса"""
    query = update.callback_query
    await query.answer()
    
    user_id = query.from_user.id
    data = query.data
    message_id = query.message.message_id
    
    bot_logger.info("quiz callback: data=%s, user_id=%s", data, user_id)
    
    # Удаляем сообщение с кнопками
    await delete_message_safely(context, user_id, message_id)
    
    # ========== ОБРАБОТКА КНОПКИ "НАЗАД" (самая первая) ==========
    if data == "quiz_back":
        bot_logger.info("Нажата кнопка НАЗАД для user_id=%s", user_id)
        await go_back(update, context, user_id)
        return
    
    if user_id not in user_sessions:
        await context.bot.send_message(chat_id=user_id, text="❌ Сессия не найдена")
        return
    
    session = user_sessions[user_id]
    current_step = session.get("step", 0)
    
    bot_logger.info("Текущий шаг опроса: %s", current_step)
    
    # Обработка выбора прошивки
    if current_step == QuizStep.FIRMWARE.value and data.startswith("firmware_"):
        previous_session = deepcopy(session)
        firmware_key = data.replace("firmware_", "")
        from app.handlers.quiz import FIRMWARE_OPTIONS
        session["data"]["firmware"] = FIRMWARE_OPTIONS.get(firmware_key, "Не указана")
        session["step"] = QuizStep.PROTOCOL.value
        if not await persist_transition(context, user_id, previous_session):
            return
        await context.bot.send_message(chat_id=user_id, text=f"✅ Выбрана прошивка: {session['data']['firmware']}")
        last_id = await ask_question(context, user_id, QuizStep.PROTOCOL.value)
        session["last_question_id"] = last_id
        
        return
    
    # Обработка выбора протокола
    if current_step == QuizStep.PROTOCOL.value and data.startswith("protocol_"):
        previous_session = deepcopy(session)
        protocol_key = data.replace("protocol_", "")
        from app.handlers.quiz import PROTOCOL_OPTIONS
        session["data"]["protocol"] = PROTOCOL_OPTIONS.get(protocol_key, "Не указан")
        session["step"] = QuizStep.OS.value
        session["waiting_for_custom_protocol"] = protocol_key == "other"
        if not await persist_transition(context, user_id, previous_session):
            return
        
        if protocol_key == "other":
            msg = await context.bot.send_message(
                chat_id=user_id,
                text="✏️ Напишите название протокола:"
            )
            session["last_question_id"] = msg.message_id
        else:
            await context.bot.send_message(chat_id=user_id, text=f"✅ Выбран протокол: {session['data']['protocol']}")
            last_id = await ask_question(context, user_id, QuizStep.OS.value)
            session["last_question_id"] = last_id
        
        return
    
    # Обработка выбора ОС
    if current_step == QuizStep.OS.value and data.startswith("os_"):
        previous_session = deepcopy(session)
        os_key = data.replace("os_", "")
        from app.handlers.quiz import OS_OPTIONS
        session["data"]["os"] = OS_OPTIONS.get(os_key, "Не указана")
        session["step"] = QuizStep.DESCRIPTION.value
        session["waiting_for_custom_os"] = os_key == "other"
        if not await persist_transition(context, user_id, previous_session):
            return
        
        if os_key == "other":
            msg = await context.bot.send_message(
                chat_id=user_id,
                text="✏️ Напишите название ОС:"
            )
            session["last_question_id"] = msg.message_id
        else:
            await context.bot.send_message(chat_id=user_id, text=f"✅ Выбрана ОС: {session['data']['os']}")
            last_id = await ask_question(context, user_id, QuizStep.DESCRIPTION.value)
            session["last_question_id"] = last_id
        
        return
    
    bot_logger.warning("Необработанный quiz callback: data=%s, step=%s", data, current_step)


async def go_back(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Возврат к предыдущему вопросу"""
    bot_logger.info("go_back вызван для user_id=%s", user_id)
    
    session = user_sessions.get(user_id)
    if not session:
        await context.bot.send_message(chat_id=user_id, text="❌ Сессия не найдена")
        return
    
    current_step = session.get("step", 0)
    bot_logger.info("Текущий шаг before go_back: %s", current_step)
    
    # Нельзя вернуться с первого шага
    if current_step <= QuizStep.ROUTER.value:
        await context.bot.send_message(chat_id=user_id, text="❌ Это первый вопрос, нельзя вернуться назад")
        return
    
    previous_session = deepcopy(session)

    # Переход на предыдущий шаг
    previous_step = current_step - 1
    session["step"] = previous_step
    
    # Очищаем ответ на текущем шаге (если был)
    step_name = QuizStep.get_step_info(previous_step).get("name")
    if step_name and step_name in session["data"]:
        del session["data"][step_name]
        bot_logger.info("Удалён ответ для шага %s: %s", current_step, step_name)

    if not await persist_transition(context, user_id, previous_session):
        return
    
    await context.bot.send_message(
        chat_id=user_id,
        text=f"◀️ Возврат к вопросу {session['step'] + 1} из 5"
    )
    
    # Отправляем предыдущий вопрос
    last_id = await ask_question(context, user_id, previous_step)
    session["last_question_id"] = last_id
    
    bot_logger.info("Возврат выполнен, новый шаг: %s", session["step"])
