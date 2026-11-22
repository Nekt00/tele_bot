#!/usr/bin/env python3
"""
Автоматическая проверка и миграция структуры PostgreSQL БД
Без потери данных
"""

import asyncio
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy import text
from sqlalchemy.ext.asyncio import create_async_engine
from app.config import settings
from app.database.base import Base
from app.models import UserSession, Ticket, BotGroup  # noqa: F401


async def migrate_structure():
    """Автоматическая миграция структуры"""
    print("=" * 60)
    print("🔍 ПРОВЕРКА СТРУКТУРЫ БАЗЫ ДАННЫХ")
    print("=" * 60)
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        # Создаём таблицы если их нет
        print("🔄 Создаю отсутствующие таблицы...")
        await conn.run_sync(Base.metadata.create_all)
        
        # Проверяем и добавляем новые колонки
        print("🔍 Проверяю структуру таблиц...")
        
        # Таблицы и их модели
        tables = {
            "sessions": UserSession,
            "tickets": Ticket,
            "bot_groups": BotGroup
        }
        
        for table_name, model in tables.items():
            try:
                # Получаем существующие колонки
                result = await conn.execute(text(f"""
                    SELECT column_name 
                    FROM information_schema.columns 
                    WHERE table_name = '{table_name}'
                    ORDER BY ordinal_position
                """))
                existing_cols = [row[0] for row in result.fetchall()]
                
                # Получаем колонки из модели
                model_cols = [c.name for c in model.__table__.columns]
                
                # Находим новые колонки
                new_cols = set(model_cols) - set(existing_cols)
                
                if new_cols:
                    print(f"\n  📌 Таблица {table_name}: добавляю колонки {list(new_cols)}")
                    for col_name in new_cols:
                        column = model.__table__.columns[col_name]
                        col_type = str(column.type)
                        
                        # Преобразуем тип для PostgreSQL
                        if "VARCHAR" in col_type:
                            pg_type = "TEXT"
                        elif "INTEGER" in col_type and "BIG" not in col_type:
                            pg_type = "INTEGER"
                        elif "BIGINT" in col_type:
                            pg_type = "BIGINT"
                        elif "JSON" in col_type:
                            pg_type = "JSONB"
                        elif "DATETIME" in col_type or "TIMESTAMP" in col_type:
                            pg_type = "TIMESTAMP"
                        elif "BOOLEAN" in col_type:
                            pg_type = "BOOLEAN"
                        else:
                            pg_type = "TEXT"
                        
                        try:
                            await conn.execute(text(f"""
                                ALTER TABLE {table_name} 
                                ADD COLUMN IF NOT EXISTS {col_name} {pg_type}
                            """))
                            print(f"      ✓ Добавлена: {col_name}")
                        except Exception as e:
                            print(f"      ❌ Ошибка: {col_name} - {e}")
            except Exception as e:
                print(f"  ⚠️ Таблица {table_name} не существует или ошибка: {e}")
    
    await engine.dispose()
    print("\n" + "=" * 60)
    print("✅ Структура БД обновлена, данные сохранены")
    print("=" * 60)


async def main():
    try:
        await migrate_structure()
    except Exception as e:
        print(f"\n❌ Ошибка: {e}")
        sys.exit(1)


if __name__ == "__main__":
    import subprocess

    raise SystemExit(subprocess.call([sys.executable, "-m", "alembic", "upgrade", "head"]))
