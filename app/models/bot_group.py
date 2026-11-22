from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, Boolean, Index, Integer, String
from typing import Optional
from .base import Base


class BotGroup(Base):
    __tablename__ = "bot_groups"
    __table_args__ = (Index("idx_bot_groups_is_active", "is_active"),)
    
    chat_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    title: Mapped[str] = mapped_column(String(255), nullable=False)
    username: Mapped[Optional[str]] = mapped_column(String(255))
    invite_link: Mapped[Optional[str]] = mapped_column(String(512))
    is_active: Mapped[bool] = mapped_column(Boolean, default=True)
    member_count: Mapped[Optional[int]] = mapped_column(Integer, default=0)
