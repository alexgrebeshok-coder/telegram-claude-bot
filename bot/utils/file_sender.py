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
    """
    Извлечь пути к файлам из текста.
    
    Args:
        text: Текст ответа Claude
        
    Returns:
        Множество уникальных путей к файлам
    """
    paths = set()
    
    for pattern in FILE_PATH_PATTERNS:
        matches = re.findall(pattern, text, re.IGNORECASE | re.MULTILINE)
        for match in matches:
            # match может быть строкой или tuple (если есть группы)
            path = match if isinstance(match, str) else match[0] if match else None
            if path:
                # Очистить путь от лишних символов
                path = path.strip('\'".,;:!?()[]{}')
                
                # Проверить, что путь выглядит как файл
                if path and '.' in Path(path).name:
                    paths.add(path)
    
    return paths


def get_file_type(filepath: str) -> str:
    """
    Определить тип файла по расширению.
    
    Returns:
        'photo', 'video', 'audio', 'document'
    """
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
    """
    Отправить файл пользователю, определив тип по расширению.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        filepath: Путь к файлу
        
    Returns:
        True если файл отправлен успешно
    """
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
    """
    Найти все пути к файлам в тексте и отправить файлы пользователю.
    
    Args:
        bot: Экземпляр бота
        user_id: ID пользователя
        text: Текст ответа Claude
        
    Returns:
        Количество успешно отправленных файлов
    """
    paths = extract_file_paths(text)
    sent_count = 0
    
    for filepath in paths:
        # Проверить существование файла
        if os.path.isfile(filepath):
            success = await send_file_by_type(bot, user_id, filepath)
            if success:
                sent_count += 1
    
    if sent_count > 0:
        logger.info(f"Отправлено файлов: {sent_count} для user {user_id}")
    
    return sent_count
