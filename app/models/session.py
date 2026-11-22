from sqlalchemy.orm import Mapped, mapped_column
from sqlalchemy import BigInteger, Integer, JSON
from typing import Dict, Any
from .base import Base


class UserSession(Base):
    __tablename__ = "sessions"
    
    user_id: Mapped[int] = mapped_column(BigInteger, primary_key=True)
    step: Mapped[int] = mapped_column(Integer, default=0)
    data: Mapped[Dict[str, Any]] = mapped_column(JSON, default=dict)
