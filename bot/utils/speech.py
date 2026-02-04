"""
Утилита для распознавания речи (Speech-to-Text) с использованием whisper.cpp.
Конвертирует голосовые сообщения в текст офлайн, без API-ключей.
Использует Metal acceleration на Apple Silicon для высокой скорости.
"""
import asyncio
import logging
import os
import subprocess
import tempfile
from typing import Optional

from ..config import WHISPER_CPP_PATH, WHISPER_MODEL_PATH, WHISPER_TIMEOUT

logger = logging.getLogger(__name__)

FFMPEG_PATH = "ffmpeg"


def convert_to_wav(audio_path: str, wav_path: str = None) -> Optional[str]:
    """
    Конвертировать аудио файл в WAV 16kHz mono для надёжного распознавания.

    Args:
        audio_path: Путь к исходному аудиофайлу
        wav_path: Путь для WAV файла (опционально)

    Returns:
        Путь к WAV файлу или None при ошибке
    """
    if wav_path is None:
        base = audio_path.rsplit(".", 1)[0] if "." in audio_path else audio_path
        wav_path = base + ".wav"

    try:
        result = subprocess.run(
            [
                FFMPEG_PATH,
                "-i",
                audio_path,
                "-ar",
                "16000",
                "-ac",
                "1",
                "-f",
                "wav",
                "-y",
                wav_path,
            ],
            capture_output=True,
            text=True,
            timeout=30,
        )

        if result.returncode == 0 and os.path.exists(wav_path):
            return wav_path
        logger.error(f"Ошибка конвертации ffmpeg: {result.stderr}")
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


def _run_whisper_sync(audio_path: str) -> Optional[str]:
    """
    Синхронный вызов whisper.cpp для распознавания речи.

    Args:
        audio_path: Путь к аудиофайлу (WAV, MP3, OGG, FLAC)

    Returns:
        Распознанный текст или None при ошибке
    """
    if not os.path.exists(WHISPER_CPP_PATH):
        logger.error(f"whisper-cli не найден: {WHISPER_CPP_PATH}")
        return None

    if not os.path.exists(WHISPER_MODEL_PATH):
        logger.error(f"Модель Whisper не найдена: {WHISPER_MODEL_PATH}")
        logger.error(
            "Скачайте модель: https://huggingface.co/ggerganov/whisper.cpp"
        )
        return None

    if not os.path.exists(audio_path):
        logger.error(f"Аудиофайл не найден: {audio_path}")
        return None

    try:
        result = subprocess.run(
            [
                WHISPER_CPP_PATH,
                "-m",
                WHISPER_MODEL_PATH,
                "-f",
                audio_path,
                "-l",
                "ru",
                "-np",
                "-nt",
                "-bs",
                "1",
            ],
            capture_output=True,
            text=True,
            timeout=WHISPER_TIMEOUT,
            cwd=os.path.dirname(WHISPER_MODEL_PATH) or ".",
        )

        if result.returncode != 0:
            logger.error(f"whisper-cli ошибка: {result.stderr}")
            return None

        text = result.stdout.strip()
        if text:
            logger.info(f"Распознано (Whisper): {text[:100]}...")
            return text
        logger.warning("Речь не распознана (пустой результат)")
        return None

    except subprocess.TimeoutExpired:
        logger.error(f"Таймаут распознавания (>{WHISPER_TIMEOUT} сек)")
        return None
    except Exception as e:
        logger.error(f"Ошибка распознавания речи: {e}")
        return None


async def speech_to_text(audio_path: str) -> Optional[str]:
    """
    Распознать речь из аудиофайла с помощью whisper.cpp (офлайн, Metal).

    Args:
        audio_path: Путь к аудиофайлу (OGG, WAV, MP3, FLAC)

    Returns:
        Распознанный текст или None при ошибке
    """
    wav_path = None
    delete_wav = False

    # Конвертируем OGG в WAV для стабильности (Telegram голосовые = OGG)
    if audio_path.lower().endswith((".ogg", ".oga")):
        wav_path = convert_to_wav(audio_path)
        if not wav_path:
            return None
        audio_file = wav_path
        delete_wav = True
    else:
        audio_file = audio_path

    try:
        # Запускаем в executor, т.к. subprocess блокирующий
        loop = asyncio.get_event_loop()
        text = await loop.run_in_executor(
            None, _run_whisper_sync, audio_file
        )
        return text
    finally:
        if delete_wav and wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except OSError:
                pass


async def text_to_speech(text: str, output_path: str = None) -> Optional[str]:
    """
    Синтезировать речь из текста (опционально).

    Использует edge-tts для синтеза.

    Args:
        text: Текст для синтеза
        output_path: Путь для сохранения (опционально)

    Returns:
        Путь к MP3 файлу или None при ошибке
    """
    try:
        import edge_tts
    except ImportError:
        logger.error(
            "Модуль edge-tts не установлен. Установите: pip install edge-tts"
        )
        return None

    if output_path is None:
        output_path = tempfile.mktemp(suffix=".mp3")

    try:
        communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
        await communicate.save(output_path)

        if os.path.exists(output_path):
            return output_path
        return None

    except Exception as e:
        logger.error(f"Ошибка синтеза речи: {e}")
        return None
