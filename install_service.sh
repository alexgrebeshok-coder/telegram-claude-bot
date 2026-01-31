#!/bin/bash

# Установка Claude Telegram Bot как сервиса macOS
# Бот будет запускаться автоматически при включении компьютера

set -e

SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PLIST_NAME="com.claude-telegram-bot.plist"
PLIST_SOURCE="$SCRIPT_DIR/$PLIST_NAME"
PLIST_DEST="$HOME/Library/LaunchAgents/$PLIST_NAME"

echo "🤖 Установка Claude Telegram Bot как сервиса"
echo "=============================================="
echo ""

# Проверить что plist существует
if [ ! -f "$PLIST_SOURCE" ]; then
    echo "❌ Файл $PLIST_NAME не найден!"
    exit 1
fi

# Остановить если уже запущен
if launchctl list | grep -q "com.claude-telegram-bot"; then
    echo "⏹️  Останавливаю текущий сервис..."
    launchctl unload "$PLIST_DEST" 2>/dev/null || true
fi

# Создать директорию если нужно
mkdir -p "$HOME/Library/LaunchAgents"

# Скопировать plist
echo "📋 Копирую конфигурацию сервиса..."
cp "$PLIST_SOURCE" "$PLIST_DEST"

# Загрузить сервис
echo "🚀 Запускаю сервис..."
launchctl load "$PLIST_DEST"

# Проверить статус
sleep 2
if launchctl list | grep -q "com.claude-telegram-bot"; then
    echo ""
    echo "✅ Сервис успешно установлен и запущен!"
    echo ""
    echo "📌 Бот теперь будет:"
    echo "   • Запускаться автоматически при включении Mac"
    echo "   • Перезапускаться автоматически при сбоях"
    echo "   • Работать в фоне постоянно"
    echo ""
    echo "🔧 Команды управления:"
    echo "   Остановить:  launchctl unload $PLIST_DEST"
    echo "   Запустить:   launchctl load $PLIST_DEST"
    echo "   Статус:      launchctl list | grep claude-telegram"
    echo "   Логи:        tail -f $SCRIPT_DIR/bot.log"
else
    echo "❌ Ошибка запуска сервиса"
    echo "Проверьте логи: cat $SCRIPT_DIR/bot_error.log"
    exit 1
fi
