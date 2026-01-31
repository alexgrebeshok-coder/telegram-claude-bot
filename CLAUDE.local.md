# Telegram Claude Bot — Полный референс проекта

## Обзор

**Название:** Claude Code Telegram Bot
**Версия:** 2.0.0
**Дата создания:** Январь 2026
**GitHub:** https://github.com/alexgrebeshok-coder/telegram-claude-bot
**Лицензия:** MIT
**Статус:** Готов к продакшну

Telegram бот для удалённого взаимодействия с Claude Code на локальном компьютере через CLI.

---

## Архитектура

```
📱 Telegram (пользователь)
      │
      │  Текст/Фото/Голос/Документы
      ▼
💻 Telegram Bot (Python + aiogram)
      │
      │  subprocess
      ▼
🤖 Claude Code CLI (локально)
      │
      │  Читает/пишет файлы
      ▼
📁 Файловая система
```

**Ключевой принцип:** Claude работает локально на компьютере пользователя, имеет доступ к файлам и проектам, использует подписку Claude (не API ключ).

---

## Структура проекта

```
telegram_claude_bot/
├── bot/
│   ├── __init__.py
│   ├── claude_client.py      # Запуск Claude CLI через subprocess
│   ├── config.py             # Конфигурация из .env
│   ├── database.py           # SQLite база данных (aiosqlite)
│   ├── keyboards.py          # Telegram клавиатуры
│   ├── main.py               # Точка входа, регистрация роутеров
│   ├── models.py             # Pydantic модели (Task, User, TaskStatus)
│   ├── notifier.py           # Уведомления о задачах
│   ├── states.py             # FSM состояния
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py       # /start, /help
│   │   ├── management.py     # Управление задачами
│   │   ├── media.py          # Фото, документы, голосовые
│   │   └── tasks.py          # Обработка текстовых задач
│   └── utils/
│       ├── __init__.py
│       ├── file_sender.py    # Отправка файлов из ответов Claude
│       ├── speech.py         # Распознавание речи (Vosk)
│       └── text_formatter.py # Очистка MD-разметки
├── tests/
│   ├── __init__.py
│   ├── conftest.py
│   ├── test_config.py
│   └── test_text_formatter.py
├── .github/workflows/
│   └── ci.yml                # GitHub Actions (lint, test, docker)
├── run.py                    # Скрипт запуска
├── start.sh                  # Shell скрипт запуска
├── Dockerfile                # Docker образ
├── docker-compose.yml        # Docker Compose конфигурация
├── requirements.txt          # Python зависимости
├── .env.example              # Пример конфигурации
├── .gitignore
├── LICENSE                   # MIT
├── README.md                 # Документация
├── CHANGELOG.md              # История изменений
└── CLAUDE.local.md           # Этот файл
```

**Размер кодовой базы:** ~2500 строк Python

---

## Технический стек

| Компонент | Технология | Версия |
|-----------|------------|--------|
| Telegram API | aiogram | 3.4.1 |
| База данных | SQLite + aiosqlite | 0.19.0 |
| HTTP клиент | aiohttp | 3.9.1 |
| Валидация | Pydantic | 2.5.0 |
| Распознавание речи | Vosk | 0.3.45+ |
| Синтез речи | edge-tts | 6.1.0+ |
| Аудио обработка | pydub + ffmpeg | - |
| Python | 3.10+ | - |

---

## Возможности

### 1. Текстовые запросы
- Любое сообщение передаётся в Claude Code CLI
- Поддержка сессий (продолжить/новая)
- Выбор модели (Opus 4.5, Sonnet 4.5, Haiku 4.5)

### 2. Обработка файлов (входящие)
- **Фото** → сохраняет в `/tmp/claude_bot/photos/`, анализ через Vision
- **Документы** → сохраняет в `/tmp/claude_bot/documents/`, передаёт путь Claude
- **Голосовые** → распознаёт офлайн (Vosk), выполняет как текст
- **Аудио** → передаёт путь для обработки

### 3. Отправка файлов (исходящие)
- Автоматическое извлечение путей из ответов Claude
- Фото (.jpg, .png, .gif, .webp) → `send_photo`
- Видео (.mp4, .mov) → `send_video`
- Аудио (.mp3, .ogg) → `send_audio`
- Документы → `send_document`

### 4. Управление задачами
- История задач с фильтрацией
- Активные задачи
- Статусы: Pending → Running → Completed/Failed

### 5. Интерфейс
| Кнопка | Действие |
|--------|----------|
| 📝 Новая задача | Создать задачу через меню |
| 🔄 Продолжить диалог | Продолжить предыдущую сессию |
| 🆕 Новая сессия | Начать с чистого листа |
| 📋 Мои задачи | История задач |
| ⏳ Активные | Текущие задачи |
| 🤖 Модель | Выбор модели |

---

## Конфигурация

### .env файл
```env
# Telegram Bot
BOT_TOKEN=токен_от_BotFather
ADMIN_IDS=123456789

# Claude Code CLI
CLAUDE_WORKING_DIR=/path/to/projects
CLAUDE_TIMEOUT=600

# Database
DATABASE_URL=sqlite:///claude_bot.db

# Logging
LOG_LEVEL=INFO
```

### Claude CLI настройки
В `~/.claude/settings.json`:
```json
{
  "allowDangerouslySkipPermissions": true
}
```

---

## Ключевые модули

### bot/claude_client.py
Запускает Claude CLI через subprocess:
```python
claude -p "prompt" --model MODEL --dangerously-skip-permissions
```
- Поддержка сессий через `--session-id`
- Таймаут выполнения
- Парсинг JSON вывода

### bot/handlers/media.py
Обработка медиа-сообщений:
- `handle_photo()` — фото с Vision
- `handle_document()` — документы (до 20 МБ)
- `handle_voice()` — голосовые → Vosk → текст
- `handle_audio()` — аудио файлы

### bot/utils/file_sender.py
Извлечение и отправка файлов:
- Регулярные выражения для поиска путей в тексте
- Определение типа по расширению
- Асинхронная отправка

### bot/utils/speech.py
Распознавание речи:
- Модель: vosk-model-small-ru
- Конвертация OGG → WAV через ffmpeg
- Офлайн, без API ключей

### bot/utils/text_formatter.py
Очистка Markdown из ответов Claude для Telegram.

---

## База данных

### Таблица tasks
```sql
id          TEXT PRIMARY KEY
user_id     INTEGER
prompt      TEXT
status      TEXT  -- pending, running, completed, failed
created_at  DATETIME
started_at  DATETIME
completed_at DATETIME
result      TEXT
error       TEXT
```

### Таблица users
```sql
user_id       INTEGER PRIMARY KEY
username      TEXT
created_at    DATETIME
last_activity DATETIME
task_count    INTEGER
```

---

## CI/CD

### GitHub Actions (.github/workflows/ci.yml)
1. **lint** — ruff check bot/
2. **test** — pytest tests/ (18 тестов)
3. **docker** — docker build

### Docker
```bash
# Сборка
docker build -t telegram-claude-bot .

# Запуск
docker-compose up -d
```

---

## Развёртывание

### Локально (macOS)
```bash
# Установка
cd telegram_claude_bot
pip install -r requirements.txt
brew install ffmpeg

# Запуск
python3 run.py
# или
./start.sh
```

### Автозапуск (macOS LaunchAgent)
```bash
cp com.claude-telegram-bot.plist ~/Library/LaunchAgents/
launchctl load ~/Library/LaunchAgents/com.claude-telegram-bot.plist
```

### Docker
```bash
cp .env.example .env
# Заполнить .env
docker-compose up -d
```

---

## История версий

### v2.0.0 (30 января 2026)
- Приём файлов: фото, документы, голосовые, аудио
- Автоматическая отправка файлов из ответов Claude
- Распознавание речи (Vosk, офлайн)
- Очистка MD-разметки
- CI/CD pipeline
- Docker support
- Публикация на GitHub

### v1.0.0 (15 января 2026)
- Первый релиз
- Текстовые запросы к Claude Code
- Управление сессиями
- Выбор модели
- История задач
- SQLite база данных

---

## Временные директории

```
/tmp/claude_bot/
├── photos/      # Фото от пользователей
├── documents/   # Документы
├── voice/       # Голосовые сообщения
└── output/      # Файлы для отправки
```

---

## Команды для работы

```bash
# Запуск
python3 run.py

# Логи
tail -f bot.log

# Перезапуск (launchd)
launchctl unload ~/Library/LaunchAgents/com.claude-telegram-bot.plist
launchctl load ~/Library/LaunchAgents/com.claude-telegram-bot.plist

# Тесты
pytest tests/ -v

# Линтер
ruff check bot/
```

---

## Безопасность

- `.env` не попадает в git (в .gitignore)
- Токен бота сменён перед публикацией
- ADMIN_IDS ограничивает доступ
- Рабочая директория ограничивает область файлов
- Таймауты на выполнение задач

---

## Связанные файлы в проекте

| Файл | Назначение |
|------|------------|
| README.md | Публичная документация |
| CHANGELOG.md | История изменений |
| PLAN_FILE_EXCHANGE.md | План реализации обмена файлами |
| CHANGES_FILE_EXCHANGE.md | Детальное описание изменений v2.0 |
| _OLD_DOCS/ | Старая документация (не в git) |

---

## Контакты и ссылки

- **GitHub:** https://github.com/alexgrebeshok-coder/telegram-claude-bot
- **Claude Code:** https://docs.anthropic.com/en/docs/build-with-claude/claude-code
- **Vosk:** https://alphacephei.com/vosk/
- **aiogram:** https://aiogram.dev/

---

*Последнее обновление: 31 января 2026*
