# Реализация обмена файлами в Telegram Claude Bot

**Дата:** 30 января 2026  
**Проект:** `telegram_claude_bot/`  
**Путь:** `/Users/aleksandrgrebeshok/Проекты VScode/telegram_claude_bot/`

---

## Что было реализовано

### 1. Приём файлов от пользователя

Бот теперь принимает:
- **Фото** → сохраняет в `/tmp/claude_bot/photos/`, отправляет Claude на анализ
- **Документы** → сохраняет в `/tmp/claude_bot/documents/`, передаёт Claude путь
- **Голосовые сообщения** → распознаёт речь офлайн (Vosk), выполняет как текстовую команду
- **Аудио файлы** → передаёт Claude путь для обработки

### 2. Отправка файлов пользователю

Бот автоматически находит пути к файлам в ответах Claude и отправляет их:
- Фото (.jpg, .png, .gif, .webp) → `send_photo`
- Видео (.mp4, .mov) → `send_video`
- Аудио (.mp3, .ogg) → `send_audio`
- Документы (остальные) → `send_document`

### 3. Распознавание речи (Vosk)

- Офлайн, без API-ключей
- Русская модель: `vosk-model-small-ru`
- Конвертация OGG → WAV через ffmpeg

---

## Созданные файлы

### `bot/utils/__init__.py`

```python
"""Утилиты бота"""
from .file_sender import extract_and_send_files, send_file_by_type
from .speech import speech_to_text

__all__ = [
    "extract_and_send_files",
    "send_file_by_type",
    "speech_to_text",
]
```

### `bot/utils/file_sender.py`

```python
"""
Утилита для отправки файлов пользователю.
Извлекает пути к файлам из ответов Claude и отправляет их в Telegram.
"""
import os
import re
import logging
from pathlib import Path
from typing import Set
from aiogram import Bot
from aiogram.types import FSInputFile

logger = logging.getLogger(__name__)

# Паттерны для поиска путей к файлам в тексте
FILE_PATH_PATTERNS = [
    # Абсолютные пути Unix
    r'(?:^|[\s\'"(])(/(?:Users|home|tmp|var|opt|etc)[^\s\'"<>|*?]+\.[a-zA-Z0-9]{1,10})(?:[\s\'")\n,.]|$)',
    # Пути с /tmp/
    r'(?:^|[\s\'"(])(/tmp/[^\s\'"<>|*?]+)(?:[\s\'")\n,.]|$)',
    # Упоминание "файл: путь" или "скриншот: путь"
    r'(?:файл|file|скриншот|screenshot|создан|created|saved|сохранён|сохранен)[:\s]+[\'"]?([^\s\'"<>|*?\n]+\.[a-zA-Z0-9]{1,10})[\'"]?',
    # Пути в кавычках
    r'[\'"]([^\'"<>|*?\n]+\.[a-zA-Z0-9]{1,10})[\'"]',
    # Markdown ссылки ![](path) или [text](path)
    r'\[.*?\]\(([^\s\)<>|*?]+\.[a-zA-Z0-9]{1,10})\)',
]

# Расширения файлов по типам
IMAGE_EXTENSIONS = {'.jpg', '.jpeg', '.png', '.gif', '.webp', '.bmp', '.tiff'}
VIDEO_EXTENSIONS = {'.mp4', '.mov', '.avi', '.mkv', '.webm'}
AUDIO_EXTENSIONS = {'.mp3', '.ogg', '.wav', '.m4a', '.flac', '.aac'}
DOCUMENT_EXTENSIONS = {'.pdf', '.doc', '.docx', '.xls', '.xlsx', '.ppt', '.pptx', '.txt', '.csv', '.json', '.xml', '.html', '.md', '.py', '.js', '.ts', '.zip', '.tar', '.gz'}


def extract_file_paths(text: str) -> Set[str]:
    """Извлечь пути к файлам из текста."""
    paths = set()
    
    for pattern in FILE_PATH_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            path = match if isinstance(match, str) else match[0] if match else None
            if path:
                path = path.strip('\'".,;:!?()[]{}')
                if path and '.' in Path(path).name:
                    paths.add(path)
    
    return paths


def get_file_type(filepath: str) -> str:
    """Определить тип файла по расширению."""
    ext = Path(filepath).suffix.lower()
    
    if ext in IMAGE_EXTENSIONS:
        return 'photo'
    elif ext in VIDEO_EXTENSIONS:
        return 'video'
    elif ext in AUDIO_EXTENSIONS:
        return 'audio'
    else:
        return 'document'


async def send_file_by_type(bot: Bot, user_id: int, filepath: str) -> bool:
    """Отправить файл пользователю, определив тип по расширению."""
    if not os.path.isfile(filepath):
        logger.warning(f"Файл не найден: {filepath}")
        return False
    
    try:
        file = FSInputFile(filepath)
        file_type = get_file_type(filepath)
        filename = Path(filepath).name
        
        if file_type == 'photo':
            await bot.send_photo(user_id, file, caption=f"📷 {filename}")
        elif file_type == 'video':
            await bot.send_video(user_id, file, caption=f"🎬 {filename}")
        elif file_type == 'audio':
            await bot.send_audio(user_id, file, caption=f"🎵 {filename}")
        else:
            await bot.send_document(user_id, file, caption=f"📄 {filename}")
        
        logger.info(f"Файл отправлен: {filepath} -> user {user_id}")
        return True
        
    except Exception as e:
        logger.error(f"Ошибка отправки файла {filepath}: {e}")
        return False


async def extract_and_send_files(bot: Bot, user_id: int, text: str) -> int:
    """Найти все пути к файлам в тексте и отправить файлы пользователю."""
    paths = extract_file_paths(text)
    sent_count = 0
    
    for filepath in paths:
        if os.path.isfile(filepath):
            success = await send_file_by_type(bot, user_id, filepath)
            if success:
                sent_count += 1
    
    if sent_count > 0:
        logger.info(f"Отправлено файлов: {sent_count} для user {user_id}")
    
    return sent_count
```

### `bot/utils/speech.py`

```python
"""
Утилита для распознавания речи (Speech-to-Text) с использованием Vosk.
Конвертирует голосовые сообщения в текст офлайн, без API-ключей.
"""
import os
import json
import wave
import logging
import subprocess
import tempfile
from pathlib import Path

logger = logging.getLogger(__name__)

FFMPEG_PATH = "ffmpeg"
VOSK_MODEL_PATH = Path(__file__).parent.parent.parent / "vosk-model-small-ru"

_vosk_model = None


def get_vosk_model():
    """Получить модель Vosk (загружает при первом вызове)."""
    global _vosk_model
    
    if _vosk_model is not None:
        return _vosk_model
    
    try:
        from vosk import Model
    except ImportError:
        logger.error("Модуль vosk не установлен. Установите: pip install vosk")
        return None
    
    model_path = str(VOSK_MODEL_PATH)
    
    if not os.path.exists(model_path):
        logger.error(f"Модель Vosk не найдена: {model_path}")
        return None
    
    try:
        logger.info(f"Загрузка модели Vosk: {model_path}")
        _vosk_model = Model(model_path)
        logger.info("Модель Vosk загружена успешно")
        return _vosk_model
    except Exception as e:
        logger.error(f"Ошибка загрузки модели Vosk: {e}")
        return None


def convert_ogg_to_wav(ogg_path: str, wav_path: str = None) -> str:
    """Конвертировать OGG файл в WAV для распознавания."""
    if wav_path is None:
        wav_path = ogg_path.replace('.ogg', '.wav').replace('.oga', '.wav')
    
    try:
        result = subprocess.run(
            [FFMPEG_PATH, '-i', ogg_path, '-ar', '16000', '-ac', '1', '-f', 'wav', '-y', wav_path],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
        else:
            logger.error(f"Ошибка конвертации: {result.stderr}")
            return None
            
    except FileNotFoundError:
        logger.error("ffmpeg не найден. Установите ffmpeg для конвертации аудио.")
        return None
    except subprocess.TimeoutExpired:
        logger.error("Таймаут конвертации аудио")
        return None
    except Exception as e:
        logger.error(f"Ошибка конвертации: {e}")
        return None


async def speech_to_text(audio_path: str) -> str:
    """Распознать речь из аудиофайла с помощью Vosk (офлайн)."""
    try:
        from vosk import KaldiRecognizer
    except ImportError:
        logger.error("Модуль vosk не установлен.")
        return None
    
    model = get_vosk_model()
    if model is None:
        return None
    
    wav_path = None
    delete_wav = False
    
    if audio_path.endswith(('.ogg', '.oga')):
        wav_path = convert_ogg_to_wav(audio_path)
        if not wav_path:
            return None
        audio_file = wav_path
        delete_wav = True
    else:
        audio_file = audio_path
    
    try:
        wf = wave.open(audio_file, "rb")
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part_result = json.loads(rec.Result())
                if part_result.get("text"):
                    results.append(part_result["text"])
        
        final_result = json.loads(rec.FinalResult())
        if final_result.get("text"):
            results.append(final_result["text"])
        
        wf.close()
        
        text = " ".join(results).strip()
        
        if text:
            logger.info(f"Распознано (Vosk): {text[:100]}...")
            return text
        else:
            logger.warning("Речь не распознана (пустой результат)")
            return None
        
    except Exception as e:
        logger.error(f"Ошибка распознавания речи: {e}")
        return None
    finally:
        if delete_wav and wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass


async def text_to_speech(text: str, output_path: str = None) -> str:
    """Синтезировать речь из текста (edge-tts)."""
    try:
        import edge_tts
    except ImportError:
        logger.error("Модуль edge-tts не установлен.")
        return None
    
    if output_path is None:
        output_path = tempfile.mktemp(suffix='.mp3')
    
    try:
        communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
        await communicate.save(output_path)
        
        if os.path.exists(output_path):
            return output_path
        return None
        
    except Exception as e:
        logger.error(f"Ошибка синтеза речи: {e}")
        return None
```

### `bot/handlers/media.py`

```python
"""
Обработчики медиа-сообщений: фото, документы, голосовые.
"""
import os
import logging
import uuid
from datetime import datetime
from pathlib import Path
from aiogram import Router, F, Bot
from aiogram.types import Message

from ..models import Task, TaskStatus
from ..database import Database
from ..keyboards import main_menu
from ..utils.speech import speech_to_text

logger = logging.getLogger(__name__)
router = Router()

TEMP_DIR = Path("/tmp/claude_bot")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

(TEMP_DIR / "photos").mkdir(exist_ok=True)
(TEMP_DIR / "documents").mkdir(exist_ok=True)
(TEMP_DIR / "voice").mkdir(exist_ok=True)
(TEMP_DIR / "output").mkdir(exist_ok=True)

db = Database()


async def _execute_task_with_file(message: Message, prompt: str, file_path: str = None):
    """Выполнить задачу с файлом."""
    from .tasks import (
        _bot, db, user_sessions, user_models, 
        AVAILABLE_MODELS, DEFAULT_MODEL,
        claude_client, send_result
    )
    
    user_id = message.from_user.id
    
    task_id = str(uuid.uuid4())[:8]
    task = Task(
        id=task_id,
        user_id=user_id,
        prompt=prompt,
        status=TaskStatus.PENDING,
        created_at=datetime.now()
    )
    db.add_task(task)
    
    status_msg = await message.answer("⏳ Обрабатываю...")
    
    try:
        db.update_task(task.id, TaskStatus.RUNNING)
        
        session_id = user_sessions.get(user_id)
        model_key = user_models.get(user_id, DEFAULT_MODEL)
        model = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL])
        
        claude_client.set_model(model)
        
        from ..config import CLAUDE_TIMEOUT
        result = await claude_client.execute_task(
            prompt=prompt,
            session_id=session_id,
            timeout=CLAUDE_TIMEOUT
        )
        
        try:
            await status_msg.delete()
        except:
            pass
        
        if result.get("success"):
            new_session_id = result.get("session_id")
            if new_session_id:
                user_sessions[user_id] = new_session_id
            
            response_text = result.get("result", "")
            db.update_task(task.id, TaskStatus.COMPLETED, result=response_text)
            
            await send_result(user_id, response_text)
        else:
            error_msg = result.get("error", "Ошибка")
            db.update_task(task.id, TaskStatus.FAILED, error=error_msg)
            await _bot.send_message(user_id, f"❌ {error_msg}", reply_markup=main_menu())
    
    except Exception as e:
        logger.error(f"Ошибка обработки медиа: {e}")
        db.update_task(task.id, TaskStatus.FAILED, error=str(e))
        
        try:
            await status_msg.delete()
        except:
            pass
        
        from .tasks import _bot
        await _bot.send_message(user_id, "❌ Ошибка обработки.", reply_markup=main_menu())


@router.message(F.photo)
async def handle_photo(message: Message):
    """Обработка фото"""
    user_id = message.from_user.id
    photo = message.photo[-1]
    file_id = photo.file_id
    
    from .tasks import _bot
    
    try:
        file = await _bot.get_file(file_id)
        file_path = file.file_path
        
        ext = Path(file_path).suffix or '.jpg'
        local_path = TEMP_DIR / "photos" / f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Фото сохранено: {local_path}")
        
        caption = message.caption or "Проанализируй это изображение"
        prompt = f"{caption}\n\nИзображение: {local_path}"
        
        await _execute_task_with_file(message, prompt, str(local_path))
        
    except Exception as e:
        logger.error(f"Ошибка обработки фото: {e}")
        await message.answer("❌ Ошибка загрузки фото", reply_markup=main_menu())


@router.message(F.document)
async def handle_document(message: Message):
    """Обработка документов"""
    user_id = message.from_user.id
    document = message.document
    
    if document.file_size > 20 * 1024 * 1024:
        await message.answer("⚠️ Файл слишком большой (макс. 20 МБ)", reply_markup=main_menu())
        return
    
    from .tasks import _bot
    
    try:
        file = await _bot.get_file(document.file_id)
        file_path = file.file_path
        
        original_name = document.file_name or "file"
        safe_name = "".join(c for c in original_name if c.isalnum() or c in '._-')
        local_path = TEMP_DIR / "documents" / f"{user_id}_{uuid.uuid4().hex[:8]}_{safe_name}"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Документ сохранён: {local_path}")
        
        caption = message.caption or f"Вот файл для работы: {original_name}"
        prompt = f"{caption}\n\nФайл: {local_path}"
        
        await _execute_task_with_file(message, prompt, str(local_path))
        
    except Exception as e:
        logger.error(f"Ошибка обработки документа: {e}")
        await message.answer("❌ Ошибка загрузки документа", reply_markup=main_menu())


@router.message(F.voice)
async def handle_voice(message: Message):
    """Обработка голосовых сообщений"""
    user_id = message.from_user.id
    voice = message.voice
    
    from .tasks import _bot
    
    try:
        file = await _bot.get_file(voice.file_id)
        file_path = file.file_path
        
        local_path = TEMP_DIR / "voice" / f"{user_id}_{uuid.uuid4().hex[:8]}.ogg"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Голосовое сохранено: {local_path}")
        
        status_msg = await message.answer("🎤 Распознаю речь...")
        
        text = await speech_to_text(str(local_path))
        
        try:
            await status_msg.delete()
        except:
            pass
        
        if text:
            await message.answer(f"📝 Распознано:\n{text}")
            await _execute_task_with_file(message, text)
        else:
            await message.answer(
                "⚠️ Не удалось распознать речь. Попробуйте говорить чётче или отправьте текстом.",
                reply_markup=main_menu()
            )
        
        try:
            os.remove(local_path)
        except:
            pass
            
    except Exception as e:
        logger.error(f"Ошибка обработки голосового: {e}")
        await message.answer("❌ Ошибка обработки голосового сообщения", reply_markup=main_menu())


@router.message(F.video)
async def handle_video(message: Message):
    """Обработка видео"""
    await message.answer(
        "⚠️ Видео пока не поддерживается.\n"
        "Отправьте скриншот или текстовое описание.",
        reply_markup=main_menu()
    )


@router.message(F.audio)
async def handle_audio(message: Message):
    """Обработка аудио файлов"""
    user_id = message.from_user.id
    audio = message.audio
    
    from .tasks import _bot
    
    try:
        file = await _bot.get_file(audio.file_id)
        file_path = file.file_path
        
        ext = Path(file_path).suffix or '.mp3'
        local_path = TEMP_DIR / "voice" / f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Аудио сохранено: {local_path}")
        
        caption = message.caption or "Вот аудиофайл для работы"
        prompt = f"{caption}\n\nАудио файл: {local_path}"
        
        await _execute_task_with_file(message, prompt, str(local_path))
        
    except Exception as e:
        logger.error(f"Ошибка обработки аудио: {e}")
        await message.answer("❌ Ошибка загрузки аудио", reply_markup=main_menu())
```

---

## Изменения в существующих файлах

### `bot/main.py`

**Добавлено:**
```python
from .handlers import commands, tasks, management, media  # добавлен media
```

```python
# Регистрация роутеров
dp.include_router(commands.router)
dp.include_router(media.router)  # До tasks.router — приоритет для медиа
dp.include_router(tasks.router)
dp.include_router(management.router)
```

### `bot/handlers/tasks.py`

**Добавлен импорт:**
```python
from ..utils.file_sender import extract_and_send_files
```

**Изменена функция `send_result`:**
```python
async def send_result(user_id: int, result: str):
    """Отправить результат"""
    if not _bot:
        return
    
    if len(result) <= 4000:
        await _bot.send_message(user_id, result, reply_markup=main_menu())
    else:
        chunks = split_message(result, 4000)
        for chunk in chunks:
            await _bot.send_message(user_id, chunk)
        await _bot.send_message(user_id, "—", reply_markup=main_menu())
    
    # Найти и отправить файлы из ответа Claude
    await extract_and_send_files(_bot, user_id, result)
```

### `requirements.txt`

**Добавлено:**
```
# Медиа обработка
edge-tts>=6.1.0
vosk>=0.3.45
pydub>=0.25.1
```

### `~/Library/LaunchAgents/com.claude-telegram-bot.plist`

**Обновлён PATH:**
```xml
<key>PATH</key>
<string>/opt/homebrew/bin:/usr/local/bin:/usr/bin:/bin:/Users/aleksandrgrebeshok/.local/bin</string>
```

---

## Установленные зависимости

```bash
# Python пакеты
pip install vosk edge-tts pydub

# Системные
brew install ffmpeg
```

## Модель Vosk

Скачана с https://alphacephei.com/vosk/models и распакована:
```
telegram_claude_bot/vosk-model-small-ru/
├── README
├── am/
├── conf/
├── graph/
└── ivector/
```

---

## Структура после изменений

```
telegram_claude_bot/
├── bot/
│   ├── handlers/
│   │   ├── __init__.py
│   │   ├── commands.py
│   │   ├── management.py
│   │   ├── media.py          ← НОВЫЙ
│   │   └── tasks.py          ← ИЗМЕНЁН
│   ├── utils/                ← НОВАЯ ПАПКА
│   │   ├── __init__.py
│   │   ├── file_sender.py
│   │   └── speech.py
│   ├── __init__.py
│   ├── claude_client.py
│   ├── config.py
│   ├── database.py
│   ├── keyboards.py
│   ├── main.py               ← ИЗМЕНЁН
│   ├── models.py
│   ├── notifier.py
│   └── states.py
├── vosk-model-small-ru/      ← МОДЕЛЬ VOSK
├── requirements.txt          ← ИЗМЕНЁН
└── ...
```

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

## Тестирование

- [ ] Отправить фото — бот анализирует
- [ ] Отправить PDF — бот читает
- [ ] Запрос «сделай скриншот» — бот присылает картинку
- [ ] Запрос «создай PDF/файл» — бот присылает файл
- [ ] Голосовое сообщение — распознавание и ответ

---

## Известные проблемы

1. **ffmpeg должен быть в PATH** — добавлен `/opt/homebrew/bin` в plist
2. **Vosk требует модель** — должна лежать в `telegram_claude_bot/vosk-model-small-ru/`

---

## Команды для перезапуска

```bash
# Перезапуск бота
launchctl unload ~/Library/LaunchAgents/com.claude-telegram-bot.plist
launchctl load ~/Library/LaunchAgents/com.claude-telegram-bot.plist

# Проверка логов
tail -f /Users/aleksandrgrebeshok/Проекты\ VScode/telegram_claude_bot/bot.log
```
