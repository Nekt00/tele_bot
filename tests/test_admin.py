import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock

os.environ.setdefault("TOKEN", "test-token")

from telegram import ChatMember

from app.handlers.admin import admin_callback_handler, admin_panel, get_admin_groups


class FakeBot:
    def __init__(self, statuses):
        self.statuses = statuses

    async def get_chat_member(self, chat_id, user_id):
        return SimpleNamespace(status=self.statuses[(chat_id, user_id)])


class AdminAuthorizationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        self.groups = {-1001: {"title": "One"}, -1002: {"title": "Two"}}
        self.context = SimpleNamespace(
            bot=FakeBot({
                (-1001, 42): ChatMember.ADMINISTRATOR,
                (-1002, 42): ChatMember.MEMBER,
            }),
            bot_data={"bot_groups": self.groups},
        )

    async def test_panel_contains_only_groups_administered_by_user(self):
        groups = await get_admin_groups(self.context, 42)
        self.assertEqual(list(groups), [-1001])

        message = SimpleNamespace(reply_text=AsyncMock())
        update = SimpleNamespace(
            effective_chat=SimpleNamespace(type="private"),
            effective_user=SimpleNamespace(id=42),
            message=message,
        )
        await admin_panel(update, self.context)

        markup = message.reply_text.await_args.kwargs["reply_markup"]
        callbacks = [button.callback_data for row in markup.inline_keyboard for button in row]
        self.assertIn("group_-1001", callbacks)
        self.assertNotIn("group_-1002", callbacks)

    async def test_forged_callback_is_rejected(self):
        query = SimpleNamespace(
            data="stats_-1002",
            answer=AsyncMock(),
            edit_message_text=AsyncMock(),
            message=SimpleNamespace(delete=AsyncMock()),
        )
        update = SimpleNamespace(callback_query=query, effective_user=SimpleNamespace(id=42))

        await admin_callback_handler(update, self.context)

        self.assertIn("нет прав", query.edit_message_text.await_args.args[0])
