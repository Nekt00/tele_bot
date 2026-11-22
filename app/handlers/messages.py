"""Обработчики текстовых сообщений"""
import asyncio
from copy import deepcopy
from datetime import datetime
from telegram import Update, InlineKeyboardButton, InlineKeyboardMarkup
from telegram.ext import ContextTypes
from app.config import settings
from app.utils.logger import bot_logger
from app.handlers.callbacks import save_session_to_db, start_quiz_session, user_sessions
from app.handlers.quiz import ask_question
from app.enums import QuizStep
from app.database import session_scope
from app.repositories import TicketRepository
from app.services import SessionService
from app.handlers.free_mode import send_free_description_instruction
from app.handlers.welcome import (
    clear_user_awaiting_choice,
    delete_pending_welcome,
    is_user_awaiting_choice,
)
from app.utils.deep_links import parse_quiz_payload


async def delete_message_after_delay(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int, delay: int = 5):
    await asyncio.sleep(delay)
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def delete_message_safely(context: ContextTypes.DEFAULT_TYPE, chat_id: int, message_id: int) -> None:
    try:
        await context.bot.delete_message(chat_id=chat_id, message_id=message_id)
    except Exception:
        pass


async def resume_quiz(context: ContextTypes.DEFAULT_TYPE, user_id: int):
    session = user_sessions.get(user_id)
    if not session or session.get("mode") != "quiz":
        return
    step = session.get("step", 0)
    last_id = await ask_question(context, user_id, step)
    session["last_question_id"] = last_id
    await save_session_to_db(user_id, session)


async def is_valid_quiz_target(
    context: ContextTypes.DEFAULT_TYPE,
    user_id: int,
    group_chat_id: int,
) -> bool:
    group = context.bot_data.get("bot_groups", {}).get(group_chat_id)
    if not group or group.get("is_active", True) is False:
        return False

    try:
        member = await context.bot.get_chat_member(group_chat_id, user_id)
    except Exception as exc:
        bot_logger.warning(
            "Не удалось проверить пользователя %s в группе %s: %s",
            user_id,
            group_chat_id,
            exc,
        )
        return False
    return member.status not in {"left", "kicked"}


async def finish_quiz(update: Update, context: ContextTypes.DEFAULT_TYPE, user_id: int):
    """Завершение опроса и отправка итога в группу + сохранение в БД"""
    session = user_sessions.get(user_id)
    if not session:
        await update.message.reply_text("❌ Сессия не найдена")
        return
    
    data = session.get("data", {})
    group_chat_id = session.get("group_chat_id")
    first_name = session.get("first_name", "Пользователь")
    username = session.get("username", "нет username")
    
    # Проверяем, что есть описание проблемы
    problem_description = data.get("problem_description")
    if not problem_description:
        await update.message.reply_text("❌ Описание проблемы не найдено. Попробуйте ещё раз.")
        return
    
    now = datetime.now()
    date_time = now.strftime("%d.%m.%Y %H:%M:%S")
    
    # Получаем ссылку на группу
    try:
        invite_link = await context.bot.create_chat_invite_link(
            chat_id=group_chat_id,
            member_limit=1,
            expire_date=None
        )
        invite_url = invite_link.invite_link
    except Exception as e:
        bot_logger.info(f"Не удалось создать ссылку: {e}")
        invite_url = None
    
    # Формируем итоговое сообщение для группы
    summary = (
        f"🆕 Новый запрос от {first_name}\n"
        f"👤 Username: @{username}\n"
        f"📅 Дата обращения: {date_time}\n\n"
        f"📊 Собранные данные:\n"
        f"  🔹 Роутер: {data.get('router_model', 'Не указан')}\n"
        f"  🔹 Прошивка: {data.get('firmware', 'Не указана')}\n"
        f"  🔹 Протокол: {data.get('protocol', 'Не указан')}\n"
        f"  🔹 ОС: {data.get('os', 'Не указана')}\n\n"
        f"📝 Описание проблемы:\n{problem_description}"
    )
    
    # Сначала надёжно сохраняем обращение и закрываем DB-сессию пользователя.
    try:
        async with session_scope() as session_db:
            repo = TicketRepository(session_db)
            ticket = await repo.create_quiz_ticket(
                user_id=user_id,
                group_chat_id=group_chat_id,
                answers=data,
                username=username
            )
            await SessionService(session_db).clear_session(user_id)
        bot_logger.info(f"✅ Обращение сохранено в БД: ticket_id={ticket.id}")
    except Exception as e:
        bot_logger.exception("❌ Ошибка сохранения в БД: %s", e)
        await update.message.reply_text(
            "❌ Не удалось сохранить обращение. Ваши ответы не потеряны, попробуйте отправить описание ещё раз позже."
        )
        return

    delivered_to_group = True
    try:
        await context.bot.send_message(chat_id=group_chat_id, text=summary)
    except Exception as exc:
        delivered_to_group = False
        bot_logger.exception("Обращение сохранено, но не отправлено в группу %s: %s", group_chat_id, exc)
    
    # Формируем сообщение для пользователя
    user_summary = (
        f"✅ Ваше обращение сохранено{' и передано в группу' if delivered_to_group else ''}!\n\n"
        f"📅 Дата обращения: {date_time}\n\n"
        f"📋 Ваши данные:\n"
        f"  • Роутер: {data.get('router_model', 'Не указан')}\n"
        f"  • Прошивка: {data.get('firmware', 'Не указана')}\n"
        f"  • Протокол: {data.get('protocol', 'Не указан')}\n"
        f"  • ОС: {data.get('os', 'Не указана')}\n\n"
        f"📝 Описание проблемы: \n{problem_description}\n\n"
        f"Спасибо за обращение! Ожидайте ответа в группе!"
    )

    if not delivered_to_group:
        user_summary += "\n\n⚠️ Уведомление в группу отправить не удалось, но обращение доступно администраторам."
    
    if invite_url:
        keyboard = [[InlineKeyboardButton("🔙 Вернуться в чат", url=invite_url)]]
        reply_markup = InlineKeyboardMarkup(keyboard)
    else:
        reply_markup = None
    
    await update.message.reply_text(user_summary, reply_markup=reply_markup)
    
    # Очищаем сессию
    if user_id in user_sessions:
        del user_sessions[user_id]
    
async def handle_private_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_id = update.effective_user.id
    text = update.message.text.strip()
    message_id = update.message.message_id
    
    bot_logger.info(f"📩 Получено сообщение в ЛС от {user_id}: {text[:50]}")
    
    if text.startswith('/start'):
        payload = context.args[0] if context.args else None
        if payload:
            callback_target = parse_quiz_payload(payload, settings.TOKEN)
            if callback_target is None:
                await update.message.reply_text("❌ Некорректная ссылка на опрос.")
                return

            target_user_id, group_chat_id = callback_target
            if target_user_id != user_id:
                await update.message.reply_text("❌ Эта ссылка предназначена другому пользователю.")
                return

            if not await is_valid_quiz_target(context, user_id, group_chat_id):
                await update.message.reply_text(
                    "❌ Эта группа недоступна или вы больше не являетесь её участником."
                )
                return


            active_session = user_sessions.get(user_id)
            if active_session:
                active_group_id = active_session.get("group_chat_id")
                if active_group_id != group_chat_id:
                    await update.message.reply_text(
                        "❌ У вас уже есть незавершённое обращение для другой группы. Сначала завершите его."
                    )
                    return
                if active_session.get("mode") == "quiz":
                    await update.message.reply_text("👋 Продолжим незавершённый опрос.")
                    await resume_quiz(context, user_id)
                    return
                await update.message.reply_text(
                    "❌ Сначала завершите свободное обращение сообщением в группе."
                )
                return

            try:
                session = await start_quiz_session(
                    user_id=user_id,
                    group_chat_id=group_chat_id,
                    first_name=update.effective_user.first_name or "Пользователь",
                    username=update.effective_user.username or "нет username",
                )
            except RuntimeError:
                await update.message.reply_text("❌ Не удалось начать опрос. Попробуйте позже.")
                return
            clear_user_awaiting_choice(context, group_chat_id, user_id)
            await delete_pending_welcome(group_chat_id, user_id)
            last_id = await ask_question(context, user_id, QuizStep.ROUTER.value)
            session["last_question_id"] = last_id
            await save_session_to_db(user_id, session)
            return

        if user_id in user_sessions and user_sessions[user_id].get("mode") == "quiz":
            await update.message.reply_text(
                f"👋 Продолжим опрос.\n\nТы остановился на вопросе {user_sessions[user_id].get('step', 0) + 1} из 5"
            )
            await resume_quiz(context, user_id)
        else:
            await update.message.reply_text(
                "👋 Привет! Чтобы начать опрос, вступи в группу и нажми 'Пройти опрос'."
            )
        return
    
    if user_id not in user_sessions or user_sessions[user_id].get("mode") != "quiz":
        await update.message.reply_text(
            "❌ Нет активного опроса.\n\nЧтобы начать, вступи в группу и нажми 'Пройти опрос'."
        )
        return
    
    session = user_sessions[user_id]
    step = session.get("step", 0)
    
    asyncio.create_task(delete_message_after_delay(context, user_id, message_id, settings.DELETE_DELAYS["user_message"]))
    
    if session.get("last_question_id"):
        await delete_message_safely(context, user_id, session["last_question_id"])
    
    # Кастомный протокол
    if session.get("waiting_for_custom_protocol"):
        previous_session = deepcopy(session)
        session["data"]["protocol"] = text
        session["waiting_for_custom_protocol"] = False
        session["step"] = QuizStep.OS.value
        if not await save_session_to_db(user_id, session):
            user_sessions[user_id] = previous_session
            await update.message.reply_text("❌ Не удалось сохранить ответ. Попробуйте ещё раз позже.")
            return
        await update.message.reply_text(f"✅ Сохранено: {text}")
        last_id = await ask_question(context, user_id, QuizStep.OS.value)
        session["last_question_id"] = last_id
        return
    
    # Кастомная ОС
    if session.get("waiting_for_custom_os"):
        previous_session = deepcopy(session)
        session["data"]["os"] = text
        session["waiting_for_custom_os"] = False
        session["step"] = QuizStep.DESCRIPTION.value
        if not await save_session_to_db(user_id, session):
            user_sessions[user_id] = previous_session
            await update.message.reply_text("❌ Не удалось сохранить ответ. Попробуйте ещё раз позже.")
            return
        await update.message.reply_text(f"✅ Сохранено: {text}")
        last_id = await ask_question(context, user_id, QuizStep.DESCRIPTION.value)
        session["last_question_id"] = last_id
        return
    
    # Шаг 1: модель роутера
    if step == QuizStep.ROUTER.value:
        previous_session = deepcopy(session)
        session["data"]["router_model"] = text
        session["step"] = QuizStep.FIRMWARE.value
        if not await save_session_to_db(user_id, session):
            user_sessions[user_id] = previous_session
            await update.message.reply_text("❌ Не удалось сохранить ответ. Попробуйте ещё раз позже.")
            return
        await update.message.reply_text(f"✅ Модель сохранена: {text}")
        from app.keyboards.quiz_keyboards import get_firmware_keyboard
        msg = await context.bot.send_message(
            chat_id=user_id,
            text="2⃣ Вопрос 2 из 5:\n\nКакая прошивка установлена?",
            reply_markup=get_firmware_keyboard()
        )
        session["last_question_id"] = msg.message_id
        return
    
    # Последний шаг: описание проблемы
    if step == QuizStep.DESCRIPTION.value:
        session["data"]["problem_description"] = text
        await finish_quiz(update, context, user_id)
        return
    
    await update.message.reply_text(f"❌ Что-то пошло не так. Шаг: {step}")


async def handle_group_message(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if not update.message or not update.message.text:
        return
    
    user_id = update.message.from_user.id
    chat_id = update.message.chat_id
    
    if user_id in user_sessions and user_sessions[user_id].get("mode") == "free":
        session = user_sessions[user_id]
        if session.get("group_chat_id") != chat_id:
            return

        description = update.message.text
        first_name = session.get("first_name", "Пользователь")
        
        try:
            async with session_scope() as session_db:
                repo = TicketRepository(session_db)
                ticket = await repo.create_free_ticket(
                    user_id=user_id,
                    group_chat_id=chat_id,
                    description=description,
                    username=update.message.from_user.username
                )
                await SessionService(session_db).clear_session(user_id)
            bot_logger.info(f"✅ Свободное обращение сохранено: ticket_id={ticket.id}")
        except Exception as e:
            bot_logger.exception("❌ Ошибка сохранения: %s", e)
            await context.bot.send_message(
                chat_id=chat_id,
                text=f"❌ {first_name}, не удалось сохранить обращение. Попробуйте отправить сообщение ещё раз позже.",
            )
            return

        if session.get("instruction_msg_id"):
            await delete_message_safely(context, chat_id, session["instruction_msg_id"])

        await context.bot.send_message(
            chat_id=chat_id,
            text=f"✅ {first_name}, ваше обращение принято!"
        )
        
        del user_sessions[user_id]
        return

    if user_id in user_sessions:
        return

    if not is_user_awaiting_choice(context, chat_id, user_id):
        return

    first_name = update.message.from_user.first_name or "Пользователь"
    sent_msg = await send_free_description_instruction(
        context,
        chat_id,
        first_name,
        skipped_choice=True,
    )
    session_data = {
        "mode": "free",
        "instruction_msg_id": sent_msg.message_id,
        "group_chat_id": chat_id,
        "first_name": first_name,
    }
    if await save_session_to_db(user_id, session_data):
        user_sessions[user_id] = session_data
        clear_user_awaiting_choice(context, chat_id, user_id)
        await delete_pending_welcome(chat_id, user_id)
    else:
        await context.bot.send_message(
            chat_id=chat_id,
            text=f"❌ {first_name}, не удалось начать обращение. Попробуйте ещё раз позже.",
        )
