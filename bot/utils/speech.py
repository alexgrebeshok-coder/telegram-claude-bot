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

# Путь к ffmpeg (обычно в PATH)
FFMPEG_PATH = "ffmpeg"

# Путь к модели Vosk (русский язык)
VOSK_MODEL_PATH = Path(__file__).parent.parent.parent / "vosk-model-small-ru"

# Глобальный экземпляр модели (загружается один раз)
_vosk_model = None


def get_vosk_model():
    """
    Получить модель Vosk (загружает при первом вызове).
    """
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
        logger.error("Скачайте модель: https://alphacephei.com/vosk/models")
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
    """
    Конвертировать OGG файл в WAV для распознавания.
    
    Args:
        ogg_path: Путь к OGG файлу
        wav_path: Путь для WAV файла (опционально)
        
    Returns:
        Путь к WAV файлу
    """
    if wav_path is None:
        wav_path = ogg_path.replace('.ogg', '.wav').replace('.oga', '.wav')
    
    try:
        # Используем ffmpeg для конвертации в формат для Vosk: 16kHz, mono, 16-bit PCM
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
    """
    Распознать речь из аудиофайла с помощью Vosk (офлайн).
    
    Args:
        audio_path: Путь к аудиофайлу (OGG или WAV)
        
    Returns:
        Распознанный текст или None при ошибке
    """
    try:
        from vosk import KaldiRecognizer
    except ImportError:
        logger.error("Модуль vosk не установлен. Установите: pip install vosk")
        return None
    
    # Получить модель
    model = get_vosk_model()
    if model is None:
        return None
    
    # Если файл OGG, конвертируем в WAV
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
        # Открываем WAV файл
        wf = wave.open(audio_file, "rb")
        
        # Проверяем формат
        if wf.getnchannels() != 1 or wf.getsampwidth() != 2 or wf.getframerate() != 16000:
            logger.warning(f"Формат аудио: channels={wf.getnchannels()}, width={wf.getsampwidth()}, rate={wf.getframerate()}")
        
        # Создаём распознаватель
        rec = KaldiRecognizer(model, wf.getframerate())
        rec.SetWords(True)
        
        # Распознаём по частям
        results = []
        while True:
            data = wf.readframes(4000)
            if len(data) == 0:
                break
            if rec.AcceptWaveform(data):
                part_result = json.loads(rec.Result())
                if part_result.get("text"):
                    results.append(part_result["text"])
        
        # Финальный результат
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
        # Удалить временный WAV файл
        if delete_wav and wav_path and os.path.exists(wav_path):
            try:
                os.remove(wav_path)
            except:
                pass


async def text_to_speech(text: str, output_path: str = None) -> str:
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
        logger.error("Модуль edge-tts не установлен. Установите: pip install edge-tts")
        return None
    
    if output_path is None:
        output_path = tempfile.mktemp(suffix='.mp3')
    
    try:
        # Используем русский голос
        communicate = edge_tts.Communicate(text, "ru-RU-SvetlanaNeural")
        await communicate.save(output_path)
        
        if os.path.exists(output_path):
            return output_path
        return None
        
    except Exception as e:
        logger.error(f"Ошибка синтеза речи: {e}")
        return None
