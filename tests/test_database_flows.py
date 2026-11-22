import os
import tempfile
import unittest
from contextlib import asynccontextmanager
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import AsyncMock, patch

os.environ.setdefault("TOKEN", "test-token")

from app.database import create_engine, create_session_factory, init_db, session_scope
from app.database import session as database_session
from app.handlers import messages
from app.handlers.callbacks import save_session_to_db
from app.handlers.quiz import user_sessions
from app.models import BotGroup
from app.repositories import GroupRepository, TicketRepository
from app.services import SessionService
from app.handlers.welcome import delete_pending_welcome, save_pending_welcome
from app.models import PendingWelcome


class DatabaseFlowTests(unittest.IsolatedAsyncioTestCase):
    async def asyncSetUp(self):
        handle = tempfile.NamedTemporaryFile(suffix=".db", delete=False)
        handle.close()
        self.db_path = Path(handle.name)
        self.engine = create_engine(f"sqlite+aiosqlite:///{self.db_path}")
        self.previous_factory = database_session._session_factory
        database_session._session_factory = create_session_factory(self.engine)
        await init_db(self.engine)
        user_sessions.clear()

    async def asyncTearDown(self):
        user_sessions.clear()
        database_session._session_factory = self.previous_factory
        await self.engine.dispose()
        self.db_path.unlink(missing_ok=True)

    async def test_session_scope_commits_without_manual_commit(self):
        async with session_scope() as db:
            await GroupRepository(db).create_or_update(-1001, "Test group")

        async with session_scope() as db:
            group = await db.get(BotGroup, -1001)
        self.assertEqual(group.title, "Test group")

    async def test_saved_session_can_be_restored(self):
        data = {
            "mode": "quiz",
            "step": 2,
            "group_chat_id": -1001,
            "first_name": "Test",
            "username": "test",
            "data": {"router_model": "R1"},
        }
        self.assertTrue(await save_session_to_db(42, data))
        user_sessions.clear()

        async with session_scope() as db:
            restored = await SessionService(db).load_all_sessions_to_cache()
        user_sessions.update(restored)

        self.assertEqual(user_sessions[42]["step"], 2)
        self.assertEqual(user_sessions[42]["data"]["router_model"], "R1")

    async def test_pending_welcome_is_persisted_and_deleted(self):
        await save_pending_welcome(-1001, 42)
        async with session_scope() as db:
            self.assertIsNotNone(await db.get(PendingWelcome, (-1001, 42)))

        await delete_pending_welcome(-1001, 42)
        async with session_scope() as db:
            self.assertIsNone(await db.get(PendingWelcome, (-1001, 42)))

    async def test_ticket_queries_return_newest_record_first(self):
        async with session_scope() as db:
            repo = TicketRepository(db)
            first = await repo.create_free_ticket(42, -1001, "First")
            second = await repo.create_free_ticket(42, -1001, "Second")

        async with session_scope() as db:
            tickets = await TicketRepository(db).get_by_user(42)

        self.assertEqual([ticket.id for ticket in tickets], [second.id, first.id])

    async def test_free_ticket_is_not_confirmed_or_cleared_on_db_failure(self):
        @asynccontextmanager
        async def broken_scope():
            raise RuntimeError("database unavailable")
            yield

        user_sessions[77] = {
            "mode": "free",
            "group_chat_id": -1001,
            "first_name": "Retry",
            "instruction_msg_id": 5,
        }
        bot = SimpleNamespace(send_message=AsyncMock(), delete_message=AsyncMock())
        update = SimpleNamespace(message=SimpleNamespace(
            text="Problem",
            chat_id=-1001,
            from_user=SimpleNamespace(id=77, username="retry"),
        ))

        with patch.object(messages, "session_scope", broken_scope):
            await messages.handle_group_message(update, SimpleNamespace(bot=bot))

        texts = [call.kwargs["text"] for call in bot.send_message.await_args_list]
        self.assertTrue(all("принято" not in text for text in texts))
        self.assertIn(77, user_sessions)
        bot.delete_message.assert_not_awaited()
