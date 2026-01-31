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

# Временная директория для файлов
TEMP_DIR = Path("/tmp/claude_bot")
TEMP_DIR.mkdir(parents=True, exist_ok=True)

# Поддиректории
(TEMP_DIR / "photos").mkdir(exist_ok=True)
(TEMP_DIR / "documents").mkdir(exist_ok=True)
(TEMP_DIR / "voice").mkdir(exist_ok=True)
(TEMP_DIR / "output").mkdir(exist_ok=True)

# Импортируем функции из tasks.py для выполнения задач
# Это делается через отложенный импорт, чтобы избежать циклических зависимостей
db = Database()


async def _execute_task_with_file(message: Message, prompt: str, file_path: str = None):
    """
    Выполнить задачу с файлом.
    Использует общую логику из tasks.py.
    """
    # Отложенный импорт для избежания циклических зависимостей
    from .tasks import (
        _bot, db, user_sessions, user_models, 
        AVAILABLE_MODELS, DEFAULT_MODEL,
        claude_client, send_result
    )
    
    user_id = message.from_user.id
    
    # Создать задачу в БД
    task_id = str(uuid.uuid4())[:8]
    task = Task(
        id=task_id,
        user_id=user_id,
        prompt=prompt,
        status=TaskStatus.PENDING,
        created_at=datetime.now()
    )
    db.add_task(task)
    
    # Показать индикатор
    status_msg = await message.answer("⏳ Обрабатываю...")
    
    try:
        db.update_task(task.id, TaskStatus.RUNNING)
        
        # Получить настройки пользователя
        session_id = user_sessions.get(user_id)
        model_key = user_models.get(user_id, DEFAULT_MODEL)
        model = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL])
        
        claude_client.set_model(model)
        
        # Выполнить
        from ..config import CLAUDE_TIMEOUT
        result = await claude_client.execute_task(
            prompt=prompt,
            session_id=session_id,
            timeout=CLAUDE_TIMEOUT
        )
        
        # Удалить индикатор
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
    
    # Получить фото максимального размера
    photo = message.photo[-1]
    file_id = photo.file_id
    
    # Скачать файл
    from .tasks import _bot
    
    try:
        file = await _bot.get_file(file_id)
        file_path = file.file_path
        
        # Создать путь для сохранения
        ext = Path(file_path).suffix or '.jpg'
        local_path = TEMP_DIR / "photos" / f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Фото сохранено: {local_path}")
        
        # Формируем промпт
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
    
    # Проверить размер (лимит Telegram API ~20MB для загрузки)
    if document.file_size > 20 * 1024 * 1024:
        await message.answer("⚠️ Файл слишком большой (макс. 20 МБ)", reply_markup=main_menu())
        return
    
    from .tasks import _bot
    
    try:
        file = await _bot.get_file(document.file_id)
        file_path = file.file_path
        
        # Сохранить с оригинальным именем
        original_name = document.file_name or "file"
        safe_name = "".join(c for c in original_name if c.isalnum() or c in '._-')
        local_path = TEMP_DIR / "documents" / f"{user_id}_{uuid.uuid4().hex[:8]}_{safe_name}"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Документ сохранён: {local_path}")
        
        # Формируем промпт
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
        
        # Сохранить голосовое
        local_path = TEMP_DIR / "voice" / f"{user_id}_{uuid.uuid4().hex[:8]}.ogg"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Голосовое сохранено: {local_path}")
        
        # Показать индикатор распознавания
        status_msg = await message.answer("🎤 Распознаю речь...")
        
        # Распознать речь
        text = await speech_to_text(str(local_path))
        
        # Удалить индикатор
        try:
            await status_msg.delete()
        except:
            pass
        
        if text:
            # Показать распознанный текст
            await message.answer(f"📝 Распознано:\n{text}")
            
            # Выполнить как обычную задачу
            await _execute_task_with_file(message, text)
        else:
            await message.answer(
                "⚠️ Не удалось распознать речь. Попробуйте говорить чётче или отправьте текстом.",
                reply_markup=main_menu()
            )
        
        # Удалить временный файл
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
        
        # Определить расширение
        ext = Path(file_path).suffix or '.mp3'
        local_path = TEMP_DIR / "voice" / f"{user_id}_{uuid.uuid4().hex[:8]}{ext}"
        
        await _bot.download_file(file_path, local_path)
        logger.info(f"Аудио сохранено: {local_path}")
        
        # Формируем промпт
        caption = message.caption or "Вот аудиофайл для работы"
        prompt = f"{caption}\n\nАудио файл: {local_path}"
        
        await _execute_task_with_file(message, prompt, str(local_path))
        
    except Exception as e:
        logger.error(f"Ошибка обработки аудио: {e}")
        await message.answer("❌ Ошибка загрузки аудио", reply_markup=main_menu())
