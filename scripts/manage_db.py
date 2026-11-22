#!/usr/bin/env python3
"""
Управление базой данных
"""

import asyncio
import sys
from pathlib import Path

# Добавляем путь к проекту
sys.path.insert(0, str(Path(__file__).parent.parent))

from sqlalchemy.ext.asyncio import create_async_engine
from sqlalchemy import text
from sqlalchemy.engine import make_url
from app.config import settings


async def create_tables():
    """Создание всех таблиц"""
    print("=" * 50)
    print("Создание таблиц базы данных")
    print("=" * 50)
    print(f"Окружение: {settings.ENVIRONMENT}")
    print(f"Тип БД: {settings.DB_TYPE}")
    print(f"URL: {make_url(settings.DATABASE_URL).render_as_string(hide_password=True)}")
    print()
    
    # Импортируем модели для регистрации в Base.metadata
    from app.models import Base
    
    print("🔄 Загрузка моделей...")
    print(f"Найдено таблиц: {list(Base.metadata.tables.keys())}")
    print()
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        print("🔄 Создание таблиц...")
        await conn.run_sync(Base.metadata.create_all)
        print("✅ Таблицы успешно созданы!")
        
        # Выводим список таблиц
        if "sqlite" in settings.DATABASE_URL:
            result = await conn.execute(text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'"))
            tables = result.fetchall()
            print("\n📊 Созданные таблицы:")
            for table in tables:
                print(f"  ✓ {table[0]}")
    
    await engine.dispose()
    print("\n✅ Готово!")


async def drop_tables():
    """Удаление всех таблиц"""
    print("=" * 50)
    print("Удаление таблиц базы данных")
    print("=" * 50)
    
    confirm = input("⚠️ Вы уверены? Это удалит ВСЕ данные! (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Операция отменена")
        return
    
    from app.models import Base
    
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        print("🔄 Удаление таблиц...")
        await conn.run_sync(Base.metadata.drop_all)
        print("✅ Таблицы удалены!")
    
    await engine.dispose()
    print("\n✅ Готово!")


async def show_tables():
    """Показать существующие таблицы"""
    engine = create_async_engine(settings.DATABASE_URL, echo=False)
    
    async with engine.begin() as conn:
        if "sqlite" in settings.DATABASE_URL:
            result = await conn.execute(
                text("SELECT name FROM sqlite_master WHERE type='table' AND name NOT LIKE 'sqlite_%'")
            )
            tables = result.fetchall()
            if tables:
                print("\n📊 Существующие таблицы:")
                for table in tables:
                    print(f"  ✓ {table[0]}")
            else:
                print("\n❌ Таблицы не найдены. Запустите: python scripts/manage_db.py create")
        else:
            result = await conn.execute(
                text("SELECT table_name FROM information_schema.tables WHERE table_schema='public'")
            )
            tables = result.fetchall()
            if tables:
                print("\n📊 Существующие таблицы:")
                for table in tables:
                    print(f"  ✓ {table[0]}")
            else:
                print("\n❌ Таблицы не найдены. Запустите: python scripts/manage_db.py create")
    
    await engine.dispose()


async def reset_tables():
    """Пересоздание таблиц"""
    print("=" * 50)
    print("Пересоздание таблиц базы данных")
    print("=" * 50)
    
    confirm = input("⚠️ Это удалит ВСЕ данные! Продолжить? (yes/no): ")
    if confirm.lower() != "yes":
        print("❌ Операция отменена")
        return
    
    await drop_tables()
    print()
    await create_tables()


async def main():
    """Основная функция"""
    if len(sys.argv) < 2:
        print("📋 Управление базой данных")
        print("=" * 50)
        print("Usage: python scripts/manage_db.py [command]")
        print("\nCommands:")
        print("  create   - Создать таблицы")
        print("  drop     - Удалить таблицы")
        print("  show     - Показать существующие таблицы")
        print("  reset    - Пересоздать таблицы")
        print("\nExamples:")
        print("  python scripts/manage_db.py create")
        print("  python scripts/manage_db.py show")
        return
    
    command = sys.argv[1]
    
    if command == "create":
        await create_tables()
    elif command == "drop":
        await drop_tables()
    elif command == "show":
        await show_tables()
    elif command == "reset":
        await reset_tables()
    else:
        print(f"❌ Неизвестная команда: {command}")
        print("Доступные команды: create, drop, show, reset")


if __name__ == "__main__":
    asyncio.run(main())
