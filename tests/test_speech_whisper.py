"""
Тесты распознавания речи через whisper.cpp.
"""
import asyncio
import os
import pytest

# Проверка наличия whisper и модели для интеграционного теста
WHISPER_CLI = os.path.join(
    os.path.dirname(__file__), "..", "whisper.cpp", "whisper-cli"
)
WHISPER_MODEL = os.path.join(
    os.path.dirname(__file__), "..", "whisper.cpp", "ggml-small-q5_1.bin"
)
JFK_SAMPLE = "/tmp/whisper.cpp/samples/jfk.mp3"


def test_speech_to_text_returns_string_or_none():
    """speech_to_text возвращает str или None."""
    from bot.utils.speech import speech_to_text

    result = asyncio.run(speech_to_text("/nonexistent/file.wav"))
    assert result is None or isinstance(result, str)


@pytest.mark.skipif(
    not os.path.exists(WHISPER_CLI) or not os.path.exists(WHISPER_MODEL),
    reason="whisper-cli или модель не установлены",
)
@pytest.mark.skipif(
    not os.path.exists(JFK_SAMPLE),
    reason="Тестовый сэмпл jfk.mp3 не найден",
)
def test_speech_to_text_with_sample():
    """Распознавание реального аудио (интеграционный тест)."""
    from bot.utils.speech import speech_to_text

    result = asyncio.run(speech_to_text(JFK_SAMPLE))
    assert result is not None
    assert isinstance(result, str)
    assert len(result) > 0
