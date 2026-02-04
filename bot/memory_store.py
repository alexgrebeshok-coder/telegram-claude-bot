"""
Общая локальная память: запись диалогов в Markdown-файлы по датам.
Директория BOT_MEMORY_DIR доступна для Claude Code и других локальных ресурсов.
"""
import logging
import os
from datetime import datetime, timedelta
from typing import Optional

logger = logging.getLogger(__name__)


def load_recent_context(
    memory_dir: Optional[str] = None,
    limit: int = 5,
) -> str:
    """
    Загрузить последние записи из памяти для контекста при новой сессии.
    Читает файлы за сегодня и вчера, возвращает последние limit блоков.

    Returns:
        Строка для префикса к промпту или пустая строка, если памяти нет.
    """
    if not memory_dir:
        from .config import BOT_MEMORY_DIR
        memory_dir = BOT_MEMORY_DIR

    if not os.path.isdir(memory_dir):
        return ""

    today = datetime.now()
    yesterday = today - timedelta(days=1)
    dates = [today.strftime("%Y-%m-%d"), yesterday.strftime("%Y-%m-%d")]

    blocks = []
    for date_str in dates:
        filepath = os.path.join(memory_dir, f"{date_str}.md")
        if not os.path.isfile(filepath):
            continue
        try:
            with open(filepath, "r", encoding="utf-8") as f:
                content = f.read()
        except OSError as e:
            logger.debug("Не удалось прочитать %s: %s", filepath, e)
            continue

        # Блоки разделены "---\n"
        raw_blocks = [b.strip() for b in content.split("---\n") if b.strip()]
        blocks.extend(raw_blocks)

    if not blocks:
        return ""

    # Берём последние limit блоков
    recent = blocks[-limit:]
    context = "\n\n---\n\n".join(recent)

    return f"[Контекст из предыдущих сессий]\n\n{context}\n\n"


def load_summary_context(
    memory_dir: Optional[str] = None,
    limit: int = 5,
    max_chars: int = 1500,
) -> str:
    """
    Загрузить summary из памяти для GLM (компактный контекст).
    Читает файл summaries.md, возвращает последние limit записей.

    Returns:
        Строка с краткими summary или пустая строка.
    """
    if not memory_dir:
        from .config import BOT_MEMORY_DIR
        memory_dir = BOT_MEMORY_DIR

    summary_file = os.path.join(memory_dir, "summaries.md")
    if not os.path.isfile(summary_file):
        return ""

    try:
        with open(summary_file, "r", encoding="utf-8") as f:
            lines = f.readlines()
    except OSError as e:
        logger.debug("Не удалось прочитать summaries: %s", e)
        return ""

    if not lines:
        return ""

    # Берём последние limit строк (каждая строка = 1 summary)
    recent = [line.strip() for line in lines[-limit:] if line.strip()]
    if not recent:
        return ""

    context = "\n".join(recent)

    # Ограничиваем общий размер
    if len(context) > max_chars:
        context = context[-max_chars:]
        # Обрезаем до начала полной строки
        newline_pos = context.find("\n")
        if newline_pos > 0:
            context = context[newline_pos + 1:]

    return f"[Краткий контекст предыдущих диалогов]\n{context}\n\n"


def append_summary_to_memory(
    summary: str,
    created_at: datetime,
    memory_dir: Optional[str] = None,
) -> None:
    """
    Добавить summary диалога в файл summaries.md.
    Каждая строка = одно summary с датой/временем.
    """
    if not summary or not summary.strip():
        return

    if not memory_dir:
        from .config import BOT_MEMORY_DIR
        memory_dir = BOT_MEMORY_DIR

    try:
        os.makedirs(memory_dir, exist_ok=True)
    except OSError as e:
        logger.warning("Не удалось создать директорию памяти %s: %s", memory_dir, e)
        return

    summary_file = os.path.join(memory_dir, "summaries.md")
    time_str = created_at.strftime("%m-%d %H:%M")
    line = f"[{time_str}] {summary.strip()}\n"

    try:
        with open(summary_file, "a", encoding="utf-8") as f:
            f.write(line)
        logger.debug("Summary записан: %s", summary_file)
    except OSError as e:
        logger.warning("Не удалось записать summary %s: %s", summary_file, e)


def append_to_memory(
    created_at: datetime,
    model_display: str,
    prompt: str,
    result: str,
    memory_dir: Optional[str] = None,
) -> None:
    """
    Добавить одну запись диалога в файл памяти за указанную дату.
    Файл: memory_dir/YYYY-MM-DD.md (по умолчанию BOT_MEMORY_DIR из config).
    """
    if not memory_dir:
        from .config import BOT_MEMORY_DIR
        memory_dir = BOT_MEMORY_DIR

    try:
        os.makedirs(memory_dir, exist_ok=True)
    except OSError as e:
        logger.warning("Не удалось создать директорию памяти %s: %s", memory_dir, e)
        return

    date_str = created_at.strftime("%Y-%m-%d")
    time_str = created_at.strftime("%H:%M")
    filename = os.path.join(memory_dir, f"{date_str}.md")

    # Экранируем возможные разделители в блоке
    prompt_esc = prompt.strip().replace("```", "` ` `")
    result_esc = result.strip().replace("```", "` ` `")

    block = (
        f"\n## {date_str} {time_str} | {model_display}\n"
        f"**Запрос:**\n{prompt_esc}\n\n"
        f"**Ответ:**\n{result_esc}\n"
        "---\n"
    )

    try:
        with open(filename, "a", encoding="utf-8") as f:
            f.write(block)
        logger.debug("Запись в память: %s", filename)
    except OSError as e:
        logger.warning("Не удалось записать в память %s: %s", filename, e)
