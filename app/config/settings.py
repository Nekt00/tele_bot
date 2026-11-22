from typing import Optional
from pydantic_settings import BaseSettings, SettingsConfigDict
from pydantic import Field, field_validator
import os
from urllib.parse import quote_plus


class Settings(BaseSettings):
    """Настройки бота"""
    
    # Telegram
    TOKEN: str = Field(..., description="Токен Telegram бота")
    
    # Окружение
    ENVIRONMENT: str = Field(default="development", description="Окружение: development или production")
    
    # База данных
    # PostgreSQL параметры (если не указан DATABASE_URL)
    POSTGRES_USER: Optional[str] = Field(default=None)
    POSTGRES_PASSWORD: Optional[str] = Field(default=None)
    POSTGRES_HOST: Optional[str] = Field(default=None)
    POSTGRES_PORT: Optional[str] = Field(default="5432")
    POSTGRES_DB: Optional[str] = Field(default=None)

    DATABASE_URL: Optional[str] = Field(default=None, description="URL подключения к БД")
    
    # Задержки удаления сообщений (секунды)
    DELETE_DELAYS: dict = Field(
        default={
            "command": 2,
            "user_message": 1,
            "temp_message": 5,
            "confirm_success": 30,
            "group_instruction": 10
        },
        description="Задержки для удаления сообщений"
    )
    
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding="utf-8",
        case_sensitive=True,
        extra="ignore"
    )
    
    @field_validator("ENVIRONMENT")
    @classmethod
    def validate_environment(cls, v: str) -> str:
        """Валидация окружения"""
        allowed = ["development", "production"]
        if v not in allowed:
            raise ValueError(f"ENVIRONMENT должен быть одним из: {allowed}")
        return v
    
    @field_validator("DATABASE_URL", mode="before")
    @classmethod
    def build_database_url(cls, v: Optional[str], info) -> str:
        """Автоматически строит DATABASE_URL если не указан напрямую"""
        if v:
            return v
        
        values = info.data
        environment = values.get("ENVIRONMENT", "development")
        
        # For production - try to get from environment variables directly
        if environment == "production":
            # First, try to get from the validated data (which comes from env)
            user = values.get("POSTGRES_USER")
            password = values.get("POSTGRES_PASSWORD")
            host = values.get("POSTGRES_HOST")
            port = values.get("POSTGRES_PORT", "5432")
            db = values.get("POSTGRES_DB")
            
            # If still not found, try to read directly from os.environ (bypass Pydantic)
            if not user:
                user = os.getenv("POSTGRES_USER")
            if not password:
                password = os.getenv("POSTGRES_PASSWORD")
            if not host:
                host = os.getenv("POSTGRES_HOST")
            if not db:
                db = os.getenv("POSTGRES_DB")
            
            if not all([user, password, host, db]):
                raise ValueError(
                    "Для production окружения необходимо указать POSTGRES_USER, "
                    "POSTGRES_PASSWORD, POSTGRES_HOST, POSTGRES_DB"
                )
            
            return (
                "postgresql+asyncpg://"
                f"{quote_plus(user)}:{quote_plus(password)}@{host}:{port}/{quote_plus(db)}"
            )
        
        # For development - SQLite
        return "sqlite+aiosqlite:///bot.db"
    
    @property
    def IS_PRODUCTION(self) -> bool:
        """Проверка production окружения"""
        return self.ENVIRONMENT == "production"
    
    @property
    def DB_TYPE(self) -> str:
        """Тип БД"""
        return "postgres" if self.IS_PRODUCTION else "sqlite"
    
    @property
    def SQLALCHEMY_ENGINE_OPTIONS(self) -> dict:
        """Настройки движка SQLAlchemy"""
        if self.IS_PRODUCTION:
            return {
                "pool_size": 5,
                "max_overflow": 10,
                "pool_pre_ping": True,
                "echo": False
            }
        return {
            "connect_args": {"check_same_thread": False},
            "echo": False
        }


# Создаём глобальный экземпляр настроек
settings = Settings()


# Для обратной совместимости со старым config.py
TOKEN = settings.TOKEN
IS_PRODUCTION = settings.IS_PRODUCTION
DATABASE_URL = settings.DATABASE_URL
DB_TYPE = settings.DB_TYPE
DELETE_DELAYS = settings.DELETE_DELAYS


# Функция для получения настроек (dependency injection)
def get_settings() -> Settings:
    """Возвращает экземпляр настроек"""
    return settings
