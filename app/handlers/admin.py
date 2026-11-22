from telegram import ChatMember, InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.error import TelegramError
from telegram.ext import ContextTypes
from app.database import session_scope
from app.repositories import TicketRepository
from app.utils.logger import bot_logger


ADMIN_STATUSES = {ChatMember.ADMINISTRATOR, ChatMember.OWNER}


async def is_group_admin(context: ContextTypes.DEFAULT_TYPE, chat_id: int, user_id: int) -> bool:
    try:
        member = await context.bot.get_chat_member(chat_id, user_id)
    except TelegramError as exc:
        bot_logger.warning(
            "Не удалось проверить права пользователя %s в группе %s: %s",
            user_id,
            chat_id,
            exc,
        )
        return False
    return member.status in ADMIN_STATUSES


async def get_admin_groups(context: ContextTypes.DEFAULT_TYPE, user_id: int) -> dict:
    bot_groups = context.bot_data.get("bot_groups", {})
    admin_groups = {}
    for chat_id, info in bot_groups.items():
        if await is_group_admin(context, chat_id, user_id):
            admin_groups[chat_id] = info
    return admin_groups


async def deny_callback_access(query) -> None:
    await query.edit_message_text("❌ У вас нет прав администратора для этой группы.")


def build_groups_keyboard(bot_groups: dict) -> InlineKeyboardMarkup:
    keyboard = []
    for chat_id, info in bot_groups.items():
        keyboard.append([InlineKeyboardButton(f"📌 {info['title']}", callback_data=f"group_{chat_id}")])
    keyboard.append([InlineKeyboardButton("❌ Закрыть", callback_data="close")])
    return InlineKeyboardMarkup(keyboard)


def build_group_menu_keyboard(chat_id: int) -> InlineKeyboardMarkup:
    keyboard = [
        [InlineKeyboardButton("📊 Статистика", callback_data=f"stats_{chat_id}")],
        [InlineKeyboardButton("📋 Обращения", callback_data=f"tickets_{chat_id}")],
        [InlineKeyboardButton("👥 Администраторы", callback_data=f"admins_{chat_id}")],
        [InlineKeyboardButton("◀️ Назад к группам", callback_data="back_to_groups")],
        [InlineKeyboardButton("❌ Закрыть", callback_data="close")]
    ]
    return InlineKeyboardMarkup(keyboard)


async def get_tickets_stats(group_chat_id: int):
    async with session_scope() as session:
        repo = TicketRepository(session)
        return await repo.get_stats(group_chat_id)


async def get_recent_tickets(group_chat_id: int, limit: int = 10):
    async with session_scope() as session:
        repo = TicketRepository(session)
        return await repo.get_recent(group_chat_id, limit)


async def admin_panel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("👑 Команда /admin доступна только в личных сообщениях.")
        return
    
    bot_groups = await get_admin_groups(context, update.effective_user.id)
    
    if not bot_groups:
        await update.message.reply_text("❌ Нет групп, в которых вы являетесь администратором.")
        return
    
    await update.message.reply_text(
        "👑 Панель администратора\n\nВыберите группу:",
        reply_markup=build_groups_keyboard(bot_groups)
    )


async def stats_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    if update.effective_chat.type != "private":
        await update.message.reply_text("📊 Команда /stats доступна только в личных сообщениях.")
        return
    
    bot_groups = await get_admin_groups(context, update.effective_user.id)
    
    if not bot_groups:
        await update.message.reply_text("❌ Нет групп, в которых вы являетесь администратором.")
        return
    
    for chat_id, info in bot_groups.items():
        stats = await get_tickets_stats(chat_id)
        message = f"""
📊 Статистика группы: {info['title']}

📋 Всего обращений: {stats['total']}
🆕 За сегодня: {stats['today']}
📅 За неделю: {stats['week']}
👥 Уникальные пользователи: {stats['unique_users']}
        """
        await update.message.reply_text(message)


async def admin_callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    await query.answer()
    
    data = query.data
    bot_groups = context.bot_data.get("bot_groups", {})
    user_id = update.effective_user.id
    
    bot_logger.info("Admin callback получен: %s", data)
    
    # 1. Закрыть панель
    if data == "close":
        await query.edit_message_text("❌ Панель закрыта")
        await query.message.delete()
        return
    
    # 2. Назад к списку групп
    if data == "back_to_groups":
        admin_groups = await get_admin_groups(context, user_id)
        if not admin_groups:
            await deny_callback_access(query)
            return
        await query.edit_message_text(
            "👑 Панель администратора\n\nВыберите группу:",
            reply_markup=build_groups_keyboard(admin_groups)
        )
        return

    callback_prefixes = ("back_", "group_", "stats_", "tickets_", "admins_")
    chat_id = None
    for prefix in callback_prefixes:
        if data.startswith(prefix):
            try:
                chat_id = int(data.removeprefix(prefix))
            except ValueError:
                bot_logger.warning("Не удалось распарсить chat_id из callback: %s", data)
                await query.edit_message_text("❌ Некорректная команда панели.")
                return
            break

    if chat_id is not None and not await is_group_admin(context, chat_id, user_id):
        await deny_callback_access(query)
        return
    
    # 3. Назад в подменю (должен содержать число)
    if data.startswith("back_") and data != "back_to_groups":
        group_title = bot_groups.get(chat_id, {}).get('title', 'Группа')
        await query.edit_message_text(
            f"👑 Панель управления\n\nГруппа: {group_title}\n\nВыберите действие:",
            reply_markup=build_group_menu_keyboard(chat_id)
        )
        return
    
    # 4. Выбор группы
    if data.startswith("group_"):
        group_title = bot_groups.get(chat_id, {}).get('title', 'Группа')
        await query.edit_message_text(
            f"👑 Панель управления\n\nГруппа: {group_title}\n\nВыберите действие:",
            reply_markup=build_group_menu_keyboard(chat_id)
        )
        return
    
    # 5. Статистика
    if data.startswith("stats_"):
        stats = await get_tickets_stats(chat_id)
        group_title = bot_groups.get(chat_id, {}).get('title', 'Группа')
        
        message = f"""
📊 СТАТИСТИКА
Группа: {group_title}

📋 Всего: {stats['total']}
🆕 Сегодня: {stats['today']}
📅 За неделю: {stats['week']}
👥 Пользователей: {stats['unique_users']}

📝 Опросов: {stats['quiz_count']}
✏️ Свободных: {stats['free_count']}
        """
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=f"back_{chat_id}")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # 6. Обращения
    if data.startswith("tickets_"):
        tickets = await get_recent_tickets(chat_id, limit=10)
        group_title = bot_groups.get(chat_id, {}).get('title', 'Группа')
        
        if not tickets:
            message = f"📋 ОБРАЩЕНИЯ\nГруппа: {group_title}\n\n📭 Нет обращений"
        else:
            lines = [f"📋 ОБРАЩЕНИЯ\nГруппа: {group_title}\n"]
            for t in tickets[:5]:
                date = t.created_at.strftime("%d.%m %H:%M") if t.created_at else "дата неизвестна"
                username = t.username or f"user_{t.user_id}"
                t_type = "📝" if t.ticket_type == "quiz" else "✏️"
                lines.append(f"{date} {t_type} {username}")
            message = "\n".join(lines)
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=f"back_{chat_id}")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    # 7. Администраторы
    if data.startswith("admins_"):
        group_title = bot_groups.get(chat_id, {}).get('title', 'Группа')
        
        bot_logger.info("Запрос администраторов для группы %s", chat_id)
        
        try:
            admins = await context.bot.get_chat_administrators(chat_id)
            admin_list = []
            for a in admins:
                if not a.user.is_bot:
                    admin_text = f"• {a.user.full_name}"
                    if a.user.username:
                        admin_text += f" (@{a.user.username})"
                    if a.status == "creator":
                        admin_text += " 👑"
                    admin_list.append(admin_text)
            
            if admin_list:
                message = f"👥 АДМИНИСТРАТОРЫ\nГруппа: {group_title}\n\n" + "\n".join(admin_list)
            else:
                message = f"👥 АДМИНИСТРАТОРЫ\nГруппа: {group_title}\n\n❌ Нет администраторов"
        except Exception as e:
            bot_logger.exception("Ошибка получения администраторов: %s", e)
            message = f"👥 АДМИНИСТРАТОРЫ\nГруппа: {group_title}\n\n❌ Ошибка: {str(e)[:50]}"
        
        keyboard = [[InlineKeyboardButton("◀️ Назад", callback_data=f"back_{chat_id}")]]
        await query.edit_message_text(message, reply_markup=InlineKeyboardMarkup(keyboard))
        return
    
    bot_logger.warning("Неизвестный admin callback: %s", data)
