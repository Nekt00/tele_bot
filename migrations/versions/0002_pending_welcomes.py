"""Persist users who have not selected an intake mode.

Revision ID: 0002_pending_welcomes
Revises: 0001_initial
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0002_pending_welcomes"
down_revision: Union[str, None] = "0001_initial"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    if "pending_welcomes" not in sa.inspect(op.get_bind()).get_table_names():
        op.create_table(
            "pending_welcomes",
            sa.Column("chat_id", sa.BigInteger(), primary_key=True),
            sa.Column("user_id", sa.BigInteger(), primary_key=True),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )


def downgrade() -> None:
    op.drop_table("pending_welcomes")
