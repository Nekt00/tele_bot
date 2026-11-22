import os
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("TOKEN", "test-token")

from app.enums import QuizStep
from app.handlers import callbacks
from app.handlers.quiz import user_sessions


class QuizNavigationTests(unittest.IsolatedAsyncioTestCase):
    async def asyncTearDown(self):
        user_sessions.clear()

    async def test_back_removes_answer_for_destination_step(self):
        user_sessions[42] = {
            "mode": "quiz",
            "step": QuizStep.OS.value,
            "data": {"router_model": "R1", "firmware": "Stock", "protocol": "VLESS"},
        }
        context = SimpleNamespace(bot=SimpleNamespace(send_message=AsyncMock()))

        with (
            patch.object(callbacks, "ask_question", AsyncMock(return_value=99)),
            patch.object(callbacks, "save_session_to_db", AsyncMock(return_value=True)),
        ):
            await callbacks.go_back(SimpleNamespace(), context, 42)

        self.assertEqual(user_sessions[42]["step"], QuizStep.PROTOCOL.value)
        self.assertNotIn("protocol", user_sessions[42]["data"])
        self.assertEqual(user_sessions[42]["data"]["firmware"], "Stock")
