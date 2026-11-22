import asyncio
import os
import signal
from contextlib import suppress
from pathlib import Path
from telegram.ext import Application, CommandHandler, CallbackQueryHandler, MessageHandler, filters
from app.config import settings
from app.database import close_db, init_db, session_scope
from app.repositories import GroupRepository
from app.models import PendingWelcome
from app.handlers.admin import stats_command, admin_panel, admin_callback_handler
from app.handlers.messages import handle_private_message, handle_group_message
from app.handlers.welcome import greet_new_member
from app.handlers.callbacks import button_callback, quiz_button_callback
from app.handlers.quiz import user_sessions
from app.services import SessionService
from app.utils.logger import bot_logger
from app.handlers.welcome import PENDING_WELCOME_USERS_KEY


HEALTHCHECK_PATH = Path(os.getenv("HEALTHCHECK_PATH", "/tmp/neo_bot_healthy"))


async def update_healthcheck() -> None:
    while True:
        HEALTHCHECK_PATH.touch()
        await asyncio.sleep(10)


async def load_groups_to_context(app: Application) -> None:
    try:
        async with session_scope() as session:
            repo = GroupRepository(session)
            groups = await repo.get_all()
            bot_groups = {}
            for group in groups:
                bot_groups[group.chat_id] = {'title': group.title, 'is_active': group.is_active}
            app.bot_data["bot_groups"] = bot_groups
            bot_logger.info("Загружено %s групп в bot_data", len(bot_groups))
            return
    except Exception as e:
        bot_logger.exception("Ошибка загрузки групп: %s", e)
        app.bot_data["bot_groups"] = {}


async def load_sessions_to_cache() -> None:
    try:
        async with session_scope() as session:
            loaded_sessions = await SessionService(session).load_all_sessions_to_cache()
        active_sessions = {
            user_id: data
            for user_id, data in loaded_sessions.items()
            if isinstance(data, dict) and data.get("mode") in {"quiz", "free"}
        }
        user_sessions.clear()
        user_sessions.update(active_sessions)
        bot_logger.info("Восстановлено %s активных сессий", len(active_sessions))
    except Exception as exc:
        bot_logger.exception("Ошибка восстановления сессий: %s", exc)


async def load_pending_welcomes(app: Application) -> None:
    try:
        async with session_scope() as session:
            rows = await session.execute(PendingWelcome.__table__.select())
            pending = {(row.chat_id, row.user_id) for row in rows}
        app.bot_data[PENDING_WELCOME_USERS_KEY] = pending
        bot_logger.info("Восстановлено %s ожидающих приветствий", len(pending))
    except Exception as exc:
        bot_logger.exception("Ошибка восстановления ожидающих приветствий: %s", exc)
        app.bot_data[PENDING_WELCOME_USERS_KEY] = set()


def register_handlers(app: Application) -> None:
    """Регистрирует все обработчики бота."""
    app.add_handler(CommandHandler("start", handle_private_message))
    app.add_handler(CommandHandler("admin", admin_panel))
    app.add_handler(CommandHandler("stats", stats_command))

    app.add_handler(CallbackQueryHandler(quiz_button_callback, pattern="^quiz_back$"))
    app.add_handler(CallbackQueryHandler(quiz_button_callback, pattern="^(firmware_|protocol_|os_)"))
    app.add_handler(CallbackQueryHandler(button_callback, pattern="^(quiz_|free_)"))
    app.add_handler(CallbackQueryHandler(admin_callback_handler, pattern="^(group_|stats_|tickets_|admins_|back_|back_to_groups|close)"))

    app.add_handler(MessageHandler(filters.StatusUpdate.NEW_CHAT_MEMBERS, greet_new_member))
    app.add_handler(MessageHandler(filters.TEXT & filters.ChatType.PRIVATE, handle_private_message))
    app.add_handler(MessageHandler(filters.TEXT & (filters.ChatType.GROUP | filters.ChatType.SUPERGROUP), handle_group_message))


async def main():
    if not settings.IS_PRODUCTION:
        bot_logger.info("Инициализация локальной БД...")
        await init_db()
        bot_logger.info("Локальная БД готова")
    
    app = Application.builder().token(settings.TOKEN).build()
    register_handlers(app)

    bot_logger.info("Бот готов, запускаю polling...")
    
    await app.initialize()
    await app.start()
    await load_groups_to_context(app)
    await load_sessions_to_cache()
    await load_pending_welcomes(app)
    await app.updater.start_polling()
    
    bot_logger.info("Бот успешно запущен и готов к работе")
    
    stop = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGTERM, signal.SIGINT):
        with suppress(NotImplementedError):
            loop.add_signal_handler(sig, stop.set)

    healthcheck_task = asyncio.create_task(update_healthcheck())
    try:
        await stop.wait()
    finally:
        healthcheck_task.cancel()
        with suppress(asyncio.CancelledError):
            await healthcheck_task
        HEALTHCHECK_PATH.unlink(missing_ok=True)
        await app.updater.stop()
        await app.stop()
        await app.shutdown()
        await close_db()


if __name__ == "__main__":
    asyncio.run(main())
