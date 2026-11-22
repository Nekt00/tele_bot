from telegram.ext import ContextTypes


def build_free_description_text(first_name: str, *, skipped_choice: bool = False) -> str:
    prefix = "Ок! Тогда опишите проблему сами.\n\n" if skipped_choice else ""
    return (
        f"{prefix}{first_name}, напишите сообщение по шаблону:\n\n"
        "📋 Устройство/роутер:\n"
        "📋 Операционная система:\n"
        "📋 Протокол:\n"
        "📋 Симптомы:\n\n"
        "Чем подробнее опишете проблему, тем быстрее найдётся решение!"
    )


async def send_free_description_instruction(
    context: ContextTypes.DEFAULT_TYPE,
    chat_id: int,
    first_name: str,
    *,
    skipped_choice: bool = False,
):
    return await context.bot.send_message(
        chat_id=chat_id,
        text=build_free_description_text(first_name, skipped_choice=skipped_choice),
    )
