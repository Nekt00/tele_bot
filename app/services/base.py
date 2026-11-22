from typing import Optional, Dict, Any, List
from sqlalchemy.ext.asyncio import AsyncSession


class BaseService:
    """Базовый сервис"""
    
    def __init__(self, session: AsyncSession):
        self.session = session