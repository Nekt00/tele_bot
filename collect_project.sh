#!/bin/bash

OUTPUT="project_report.txt"

echo "=== СТРУКТУРА ПРОЕКТА ===" > $OUTPUT
echo "" >> $OUTPUT
find . -type f -name "*.py" | grep -v "__pycache__" | grep -v ".venv" | grep -v "bot.db" | sort >> $OUTPUT
echo "" >> $OUTPUT
echo "=== СОДЕРЖИМОЕ ФАЙЛОВ ===" >> $OUTPUT
echo "" >> $OUTPUT

for file in $(find . -type f -name "*.py" | grep -v "__pycache__" | grep -v ".venv" | grep -v "bot.db" | sort); do
    echo "=========================================" >> $OUTPUT
    echo "ФАЙЛ: $file" >> $OUTPUT
    echo "=========================================" >> $OUTPUT
    cat "$file" >> $OUTPUT
    echo "" >> $OUTPUT
    echo "" >> $OUTPUT
done

echo "Готово! Отчёт сохранён в $OUTPUT"
