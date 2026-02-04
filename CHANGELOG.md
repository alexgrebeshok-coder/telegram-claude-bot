# Changelog

All notable changes to this project will be documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.0.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [2.1.0] - 2026-01-31

### Changed
- **Распознавание речи**: Vosk заменён на whisper.cpp
  - Лучшее качество распознавания русского языка
  - Metal acceleration на Apple Silicon (M1/M2/M3)
  - Модель: ggml-small-q5_1.bin (~190 МБ, quantized)
  - Скорость: ~10× real-time на M2 (1 мин аудио = ~6 сек)

### Removed
- Зависимость `vosk` из requirements.txt
- Поддержка vosk-model-small-ru

### Added
- Конфигурация whisper.cpp в .env (WHISPER_CPP_PATH, WHISPER_MODEL_PATH, WHISPER_TIMEOUT)
- Тесты: `tests/test_speech_whisper.py`

### Documentation
- README.md: инструкции по установке whisper.cpp с Metal
- CLAUDE.local.md: обновлена документация распознавания речи
- docker-compose.yml: volume для whisper.cpp вместо Vosk

---

## [2.0.0] - 2026-01-30

### Added
- **File exchange**: Бот теперь принимает файлы от пользователей
  - Фото — сохраняет, отправляет Claude на анализ через Vision
  - Документы — сохраняет, передаёт Claude путь для чтения
  - Голосовые сообщения — распознаёт офлайн через Vosk, выполняет как текстовую команду
  - Аудио файлы — передаёт путь для обработки
- **File sending**: Автоматическая отправка файлов из ответов Claude
  - Фото (.jpg, .png, .gif, .webp) → send_photo
  - Видео (.mp4, .mov) → send_video
  - Аудио (.mp3, .ogg) → send_audio
  - Документы (остальные) → send_document
- **Speech recognition**: Офлайн распознавание речи через Vosk
  - Русская модель: vosk-model-small-ru
  - Конвертация OGG → WAV через ffmpeg
  - Работает без API-ключов
- **Text formatting**: Очистка Markdown-разметки из ответов Claude
  - Удаляет заголовки, жирный текст, курсив, код блоки
  - Красивое отображение в Telegram без MD-символов
- **New utilities**:
  - `bot/utils/text_formatter.py` — очистка MD-разметки
  - `bot/utils/file_sender.py` — отправка файлов в Telegram
  - `bot/utils/speech.py` — распознавание речи (Vosk)
- **New handler**: `bot/handlers/media.py` — обработка медиа-сообщений

### Changed
- **bot/handlers/tasks.py**:
  - Интегрирована очистка MD-разметки в `send_result()`
  - Автоматическая отправка файлов из ответов Claude
- **bot/main.py**: Добавлен роутер media
- **requirements.txt**: Добавлены зависимости:
  - `edge-tts>=6.1.0` (для будущего TTS)
  - `vosk>=0.3.45` (распознавание речи)
  - `pydub>=0.25.1` (обработка аудио)

### Documentation
- **README.md** полностью обновлён для публичного использования
  - Добавлены системные требования
  - Инструкция по установке Vosk модели
  - Подробное описание всех функций
  - Убраны личные пути и данные
- **CHANGELOG.md** — история изменений
- **LICENSE** — добавлена MIT лицензия
- **.gitignore** обновлён:
  - Добавлены: `*.save`, `vosk-model-small-ru/`, `vosk-model.zip`, `.env.save`

### Fixed
- Исправлена логика отправки длинных сообщений (>4000 символов)

---

## [1.0.0] - 2026-01-15

### Added
- Первый релиз
- Текстовые запросы к Claude Code через CLI
- Управление сессиями (продолжить/новая)
- Выбор модели (Opus 4.5, Sonnet 4.5, Haiku 4.5)
- История задач с фильтрацией
- Автоматический запуск через launchd (macOS)
- SQLite база данных для хранения задач
- Главное меню с кнопками
- Подтверждение опасных операций
- Команды: /start, /help, /status
