from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, Index, Integer, String, Text, JSON
from typing import Optional, Dict, Any
from .base import Base


class Ticket(Base):
    __tablename__ = "tickets"
    __table_args__ = (
        Index("idx_tickets_user_id", "user_id"),
        Index("idx_tickets_group_chat_id", "group_chat_id"),
        Index("idx_tickets_created_at", "created_at"),
    )
    
    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    user_id: Mapped[int] = mapped_column(BigInteger, nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    group_chat_id: Mapped[Optional[int]] = mapped_column(BigInteger)
    router_model: Mapped[Optional[str]] = mapped_column(Text)
    firmware: Mapped[Optional[str]] = mapped_column(Text)
    protocol: Mapped[Optional[str]] = mapped_column(Text)
    os: Mapped[Optional[str]] = mapped_column(Text)
    problem_description: Mapped[Optional[str]] = mapped_column(Text)
    extra_data: Mapped[Optional[Dict[str, Any]]] = mapped_column(JSON)
    ticket_type: Mapped[str] = mapped_column(String(50), default="quiz")
    status: Mapped[str] = mapped_column(String(50), default="new")
