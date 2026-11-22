from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column
from sqlalchemy import DateTime, func
from datetime import datetime
from typing import Any


class Base(DeclarativeBase):
    """Базовый класс для всех моделей SQLAlchemy"""
    
    __abstract__ = True
    
    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False
    )
    updated_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        onupdate=func.now(),
        nullable=False
    )
    
    def to_dict(self) -> dict[str, Any]:
        """Преобразует модель в словарь"""
        return {
            column.name: getattr(self, column.name)
            for column in self.__table__.columns
        }
