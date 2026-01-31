# Claude Code Telegram Bot

[![CI](https://github.com/YOUR_USERNAME/telegram-claude-bot/actions/workflows/ci.yml/badge.svg)](https://github.com/YOUR_USERNAME/telegram-claude-bot/actions/workflows/ci.yml)
[![Python 3.10+](https://img.shields.io/badge/python-3.10+-blue.svg)](https://www.python.org/downloads/)
[![License: MIT](https://img.shields.io/badge/License-MIT-yellow.svg)](https://opensource.org/licenses/MIT)

Telegram бот для удалённого взаимодействия с Claude Code на вашем компьютере через локальный CLI.

## Возможности

- **Текстовые запросы** к Claude Code
- **Обработка файлов**: фото, документы, аудио
- **Распознавание речи** через Vosk (офлайн, без API-ключей)
- **Автоматическая отправка файлов** из ответов Claude
- **Управление сессиями**: продолжать или начинать новые диалоги
- **Выбор модели**: Claude Opus 4.5, Sonnet 4.5, Haiku 4.5
- **История задач** и отслеживание статуса

## Как это работает

```
📱 Telegram (ты)          💻 Твой компьютер
      │                          │
      │  "Проверь config.py"     │
      │────────────────────────► │
      │                          │  Telegram Bot (Python)
      │                          │       │
      │                          │       ▼
      │                          │  subprocess запускает:
      │                          │  claude -p --dangerously-skip-permissions
      │                          │       │
      │                          │       ▼
      │                          │  Claude Code CLI
      │                          │  (работает ЛОКАЛЬНО,
      │                          │   читает/пишет ТВОИ файлы)
      │                          │       │
      │   "Файл содержит..."     │       │
      │◄─────────────────────────│◄──────┘
```

**Ключевые особенности:**
- Claude работает **локально на твоём компьютере**
- Имеет доступ к **твоим файлам и проектам**
- Использует **твою подписку Claude** (не API ключ)
- Работает **без подтверждений** (автоматически)
- **Сессии сохраняются** — можно продолжить диалог

## Системные требования

- **Python** 3.10 или выше
- **ffmpeg** для обработки аудио (для распознавания речи)
- **Claude Code CLI** должен быть установлен и настроен
- **macOS/Linux** (для автоматического запуска через launchd/systemd)

## Быстрый старт

### Docker (рекомендуется)

```bash
# Клонировать репозиторий
git clone https://github.com/YOUR_USERNAME/telegram-claude-bot.git
cd telegram-claude-bot

# Создать .env файл
cp .env.example .env
# Отредактировать .env — указать BOT_TOKEN и ADMIN_IDS

# Запустить через Docker Compose
docker-compose up -d
```

### Ручная установка

#### 1. Установка зависимостей

```bash
cd telegram_claude_bot
pip install -r requirements.txt
```

### 2. Установка системных зависимостей

**macOS:**
```bash
brew install ffmpeg
```

**Ubuntu/Debian:**
```bash
sudo apt install ffmpeg
```

### 3. Установка модели Vosk для распознавания речи

Скачайте и распакуйте русскую модель Vosk:

```bash
# Скачайте модель с https://alphacephei.com/vosk/models
# Например: vosk-model-small-ru

# Распакуйте в папку проекта
unzip vosk-model-small-ru.zip
```

Модель должна находиться в папке проекта:
```
telegram_claude_bot/
├── vosk-model-small-ru/    ← Модель Vosk
│   ├── am/
│   ├── conf/
│   ├── graph/
│   └── ivector/
└── ...
```

### 4. Настройка .env

Скопируйте пример файла и настройте его:

```bash
cp .env.example .env
```

Отредактируйте `.env`:

```env
# Telegram Bot Token (получить от @BotFather)
BOT_TOKEN=ваш_токен

# Ваш Telegram ID (можно узнать у @userinfobot)
ADMIN_IDS=123456789

# Рабочая директория Claude (где находятся ваши проекты)
CLAUDE_WORKING_DIR=/path/to/your/workspace

# Таймаут выполнения задачи в секундах (по умолчанию 10 минут)
CLAUDE_TIMEOUT=600

# Database
DATABASE_URL=sqlite:///claude_bot.db

# Logging
LOG_LEVEL=INFO
```

### 5. Настройка Claude CLI

Для автоматической работы без подтверждений в `~/.claude/settings.json` добавлено:

```json
{
  "allowDangerouslySkipPermissions": true
}
```

Это позволяет использовать флаг `--dangerously-skip-permissions` при запуске.

### 6. Запуск

**Вручную:**
```bash
python3 run.py
```

**Через скрипт:**
```bash
./start.sh
```

**Автоматический запуск (macOS):**

Скопируйте plist файл и настройте путь:

```bash
cp com.claude-telegram-bot.plist ~/Library/LaunchAgents/
# Отредактируйте пути в plist файле на свои
launchctl load ~/Library/LaunchAgents/com.claude-telegram-bot.plist
```

## Использование

### Прямые сообщения

Просто напишите боту любое сообщение — оно будет передано Claude:

```
Ты: Посмотри файл bot.py и скажи что он делает

Claude: Файл bot.py — это главный модуль Telegram бота...
```

### Кнопки меню

| Кнопка | Действие |
|--------|----------|
| 📝 Новая задача | Создать задачу через меню |
| 🔄 Продолжить диалог | Продолжить предыдущую сессию |
| 🆕 Новая сессия | Начать с чистого листа |
| 📋 Мои задачи | История задач |
| ⏳ Активные | Текущие выполняющиеся задачи |
| 🤖 Модель | Выбрать модель (Opus/Sonnet/Haiku) |

### Обработка файлов

Бот поддерживает:

- **Фото** — анализирует изображение через Claude Vision
- **Документы** (PDF, DOCX, TXT и др.) — читает и анализирует
- **Голосовые сообщения** — распознаёт через Vosk и выполняет как текст
- **Аудио файлы** — передаёт путь для обработки

Пример использования:
1. Отправьте фото с подписью "Опиши что здесь"
2. Бот проанализирует и вернёт описание
3. Если Claude создаст файл, бот автоматически его отправит

### Сессии

Каждый диалог сохраняется. Вы можете:
- **Продолжить** предыдущий разговор (Claude помнит контекст)
- **Начать новую сессию** если хотите сменить тему

## Примеры задач

```
"Проверь синтаксис в файле main.py"

"Создай функцию для парсинга JSON в utils.py"

"Найди все TODO в проекте"

"Объясни что делает функция process_data"

"Запусти тесты и покажи результат"

"Сделай git status и покажи изменения"

"Создай скриншот страницы example.com"
```

## Безопасность

⚠️ **Важно:** Бот имеет полный доступ к вашему компьютеру с правами Claude Code.

Рекомендации:
- Держите `ADMIN_IDS` только своим ID
- Не делитесь токеном бота
- Рабочая директория ограничивает область доступа
- Используйте разные рабочие директории для разных проектов
- Не публикуйте `.env` файл с секретами

## Структура проекта

```
telegram_claude_bot/
├── bot/
│   ├── claude_client.py   # Запуск Claude CLI через subprocess
│   ├── config.py          # Конфигурация
│   ├── handlers/
│   │   ├── commands.py    # /start, /help
│   │   ├── tasks.py       # Обработка задач
│   │   ├── management.py  # Управление задачами
│   │   └── media.py      # Обработка фото/документов/аудио
│   ├── utils/
│   │   ├── text_formatter.py  # Очистка MD-разметки
│   │   ├── file_sender.py     # Отправка файлов
│   │   └── speech.py         # Распознавание речи (Vosk)
│   ├── keyboards.py       # Клавиатуры Telegram
│   ├── main.py            # Запуск бота
│   ├── models.py          # Модели данных
│   ├── database.py        # SQLite база данных
│   ├── states.py          # FSM состояния
│   └── notifier.py       # Уведомления о задачах
├── vosk-model-small-ru/  # Модель Vosk (не входит в репозиторий)
├── run.py                 # Точка входа
├── start.sh               # Скрипт запуска
├── com.claude-telegram-bot.plist  # macOS LaunchAgent
├── .env.example           # Пример конфигурации
├── .gitignore            # Исключения для Git
├── requirements.txt       # Зависимости Python
├── LICENSE               # Лицензия MIT
└── README.md             # Этот файл
```

## Troubleshooting

### "Claude CLI не найден"

```bash
# Проверьте что claude установлен
which claude
claude --version
```

Установите Claude CLI если нет:
```bash
npm install -g @anthropic-ai/claude-cli
```

### "Permission denied"

Убедитесь что bypass permissions включён:
```bash
cat ~/.claude/settings.json
# Должно быть: "allowDangerouslySkipPermissions": true
```

### "Ошибка распознавания речи"

Убедитесь что ffmpeg установлен:
```bash
ffmpeg -version
```

Проверьте что модель Vosk скачана и находится в правильной папке:
```bash
ls -la vosk-model-small-ru/
```

### "Timeout"

Увеличьте `CLAUDE_TIMEOUT` в `.env` для длинных задач.

### Логи

```bash
tail -f bot.log
```

## Лицензия

MIT License - см. файл [LICENSE](LICENSE)

## Версия

- **Версия:** 2.0.0
- **Дата:** Январь 2026
- **Изменения:** См. [CHANGELOG.md](CHANGELOG.md)

## Contributing

Contributions приветствуются! Пожалуйста, создавайте pull requests или открывайте issues для улучшений.

## Благодарности

- [Claude Code CLI](https://docs.anthropic.com/en/docs/build-with-claude/claude-code) от Anthropic
- [Vosk](https://alphacephei.com/vosk/) для офлайн распознавания речи
- [aiogram](https://aiogram.dev/) для Telegram Bot API
