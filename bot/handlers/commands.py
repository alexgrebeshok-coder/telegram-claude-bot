import logging
import os
import time
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from ..keyboards import main_menu
from ..database import Database

logger = logging.getLogger(__name__)
router = Router()

db = Database()
_start_time = time.time()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    await state.clear()
    await db.add_user(message.from_user.id, message.from_user.username)

    welcome_text = (
        "👋 Привет! Я Claude Code Assistant.\n\n"
        "Просто напиши сообщение — я передам его Claude Code.\n\n"
        "Кнопки:\n"
        "🤖 Модель — Opus 4.8 / Sonnet 4.6 / Haiku 4.5 / Fable 5 / GLM\n"
        "🆕 Новая сессия — сбросить контекст\n"
        "📂 Проекты — быстрая смена папки\n"
        "📋 История — последние задачи\n"
        "ℹ️ Статус — модель, сессия, аптайм\n\n"
        "Быстрые команды:\n"
        "/pwd /ls /git /cd /run"
    )
    await message.answer(welcome_text, reply_markup=main_menu())


@router.message(Command("help"))
@router.message(F.text == "❓ Помощь")
async def help_command(message: Message):
    help_text = (
        "Просто напиши сообщение — Claude ответит.\n\n"
        "Можно:\n"
        "• Писать текст — вопросы, задачи, код\n"
        "• Слать фото/скриншоты — Claude их видит\n"
        "• Слать документы — Claude их читает\n"
        "• Голосовые сообщения — будут расшифрованы\n\n"
        "Во время выполнения — кнопка 🛑 Остановить\n"
        "При создании файлов — бот пришлёт их автоматически\n"
        "Ответы >3500 симв. — приходят как .md файл\n\n"
        "Быстрые команды:\n"
        "/pwd — текущая директория\n"
        "/ls [путь] — список файлов\n"
        "/git — git status\n"
        "/cd <путь> — сменить директорию\n"
        "/run <команда> — выполнить команду"
    )
    await message.answer(help_text, reply_markup=main_menu())


@router.message(Command("status"))
@router.message(F.text == "ℹ️ Статус")
async def status_command(message: Message):
    from ..handlers.tasks import user_sessions, get_user_model, get_model_display_name, AVAILABLE_MODELS, REMOTE_MODELS, cancel_events

    user_id = message.from_user.id
    model_key = await get_user_model(user_id)
    model_name = get_model_display_name(model_key)
    session_id = user_sessions.get(user_id) or await db.get_user_session(user_id)

    uptime_secs = int(time.time() - _start_time)
    h, m, s = uptime_secs // 3600, (uptime_secs % 3600) // 60, uptime_secs % 60

    active_tasks = len(cancel_events)
    session_str = f"`{session_id[:12]}…`" if session_id else "нет"
    working_dir = await db.get_user_working_dir(user_id)
    dir_str = os.path.basename(working_dir or os.environ.get("CLAUDE_WORKING_DIR", "~"))

    status_text = (
        f"ℹ️ Статус бота\n\n"
        f"Модель: {model_name}\n"
        f"Сессия: {session_str}\n"
        f"Активных задач: {active_tasks}\n"
        f"Аптайм: {h}ч {m}м {s}с\n"
        f"Рабочая папка: {dir_str}"
    )
    await message.answer(status_text, reply_markup=main_menu(), parse_mode="Markdown")


@router.message(F.text == "📋 История")
async def history_command(message: Message):
    user_id = message.from_user.id
    tasks = await db.get_user_tasks(user_id, limit=8)

    if not tasks:
        await message.answer("Нет задач в истории.", reply_markup=main_menu())
        return

    lines = []
    for t in tasks:
        status_icon = {"completed": "✅", "failed": "❌", "running": "⏳", "pending": "🔵"}.get(t.status.value, "•")
        prompt_preview = t.prompt[:60].replace("\n", " ")
        if len(t.prompt) > 60:
            prompt_preview += "…"
        lines.append(f"{status_icon} {prompt_preview}")

    await message.answer("Последние задачи:\n\n" + "\n".join(lines), reply_markup=main_menu())
