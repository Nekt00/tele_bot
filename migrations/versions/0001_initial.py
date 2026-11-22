"""Create the initial bot schema without replacing existing tables.

Revision ID: 0001_initial
Revises:
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "0001_initial"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    bind = op.get_bind()
    inspector = sa.inspect(bind)
    tables = set(inspector.get_table_names())

    if "sessions" not in tables:
        op.create_table(
            "sessions",
            sa.Column("user_id", sa.BigInteger(), primary_key=True),
            sa.Column("step", sa.Integer(), nullable=False, server_default="0"),
            sa.Column("data", sa.JSON(), nullable=False, server_default=sa.text("'{}'")),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if "tickets" not in tables:
        op.create_table(
            "tickets",
            sa.Column("id", sa.Integer(), primary_key=True, autoincrement=True),
            sa.Column("user_id", sa.BigInteger(), nullable=False),
            sa.Column("username", sa.String(length=255)),
            sa.Column("group_chat_id", sa.BigInteger()),
            sa.Column("router_model", sa.Text()),
            sa.Column("firmware", sa.Text()),
            sa.Column("protocol", sa.Text()),
            sa.Column("os", sa.Text()),
            sa.Column("problem_description", sa.Text()),
            sa.Column("extra_data", sa.JSON()),
            sa.Column("ticket_type", sa.String(length=50), nullable=False, server_default="quiz"),
            sa.Column("status", sa.String(length=50), nullable=False, server_default="new"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    if "bot_groups" not in tables:
        op.create_table(
            "bot_groups",
            sa.Column("chat_id", sa.BigInteger(), primary_key=True),
            sa.Column("title", sa.String(length=255), nullable=False),
            sa.Column("username", sa.String(length=255)),
            sa.Column("invite_link", sa.String(length=512)),
            sa.Column("is_active", sa.Boolean(), nullable=False, server_default=sa.true()),
            sa.Column("member_count", sa.Integer(), server_default="0"),
            sa.Column("created_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
            sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False, server_default=sa.func.now()),
        )

    inspector = sa.inspect(bind)
    index_specs = {
        "tickets": {
            "idx_tickets_user_id": ["user_id"],
            "idx_tickets_group_chat_id": ["group_chat_id"],
            "idx_tickets_created_at": ["created_at"],
        },
        "bot_groups": {"idx_bot_groups_is_active": ["is_active"]},
    }
    for table_name, indexes in index_specs.items():
        existing_indexes = {item["name"] for item in inspector.get_indexes(table_name)}
        for index_name, columns in indexes.items():
            if index_name not in existing_indexes:
                op.create_index(index_name, table_name, columns)


def downgrade() -> None:
    # This baseline may adopt a pre-existing production schema, so it must never
    # infer that those tables are safe to destroy.
    pass
