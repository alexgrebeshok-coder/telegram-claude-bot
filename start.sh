#!/bin/bash

# Claude Code Assistant Bot - Скрипт запуска
# Использование: ./start.sh

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
cd "$SCRIPT_DIR"

echo "🤖 Claude Code Assistant Bot"
echo "=============================="
echo ""

# Проверить, что .env файл существует
if [ ! -f .env ]; then
    echo "❌ Ошибка: файл .env не найден!"
    echo ""
    echo "📋 Создание .env из .env.example..."
    cp .env.example .env

    echo "✅ Файл .env создан!"
    echo ""
    echo "⚠️  Необходимо отредактировать .env и добавить:"
    echo "   1. BOT_TOKEN (получить от @BotFather в Telegram)"
    echo "   2. ADMIN_IDS (ваш Telegram ID)"
    echo ""
    echo "Запустите скрипт снова после редактирования .env"
    exit 1
fi

# Проверить, что BOT_TOKEN заполнен
if grep -q "^BOT_TOKEN=your_telegram_bot_token_here" .env 2>/dev/null; then
    echo "❌ Ошибка: BOT_TOKEN не заполнен в .env"
    echo ""
    echo "Пожалуйста:"
    echo "1. Откройте https://t.me/botfather"
    echo "2. Создайте нового бота (/newbot)"
    echo "3. Скопируйте токен в .env"
    exit 1
fi

# Проверить Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Ошибка: Python 3 не установлен"
    exit 1
fi

PYTHON_VERSION=$(python3 -c 'import sys; print(".".join(map(str, sys.version_info[:2])))')
echo "✅ Python версия: $PYTHON_VERSION"

# Проверить, что Claude CLI доступен
echo "🔍 Проверка Claude CLI..."
if command -v claude &> /dev/null; then
    CLAUDE_VERSION=$(claude --version 2>/dev/null || echo "unknown")
    echo "✅ Claude CLI доступен: $CLAUDE_VERSION"
else
    echo "❌ Ошибка: Claude CLI не найден!"
    echo ""
    echo "Убедитесь, что Claude Code установлен и доступен в PATH."
    echo "Установка: https://claude.ai/code"
    exit 1
fi

# Проверить авторизацию Claude (опционально)
echo "🔍 Проверка авторизации Claude..."
if claude --version &> /dev/null; then
    echo "✅ Claude CLI работает"
else
    echo "⚠️  Возможно Claude CLI не авторизован"
    echo "   Запустите 'claude' в терминале для авторизации"
fi

echo ""
echo "📁 Рабочая директория: $(grep CLAUDE_WORKING_DIR .env 2>/dev/null | cut -d'=' -f2 || echo '~ (по умолчанию)')"
echo ""
echo "🚀 Запуск бота..."
echo "Нажмите Ctrl+C для остановки"
echo ""

python3 run.py
