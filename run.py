#!/usr/bin/env python3
"""
Запуск Telegram бота
"""

import asyncio
import sys
from pathlib import Path

# Добавляем app в путь
sys.path.insert(0, str(Path(__file__).parent))

from app.bot import main

if __name__ == "__main__":
    print("🚀 Запуск Telegram бота...")
    print("=" * 50)
    asyncio.run(main())
