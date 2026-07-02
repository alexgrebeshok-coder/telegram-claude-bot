import asyncio
import logging
import os
import uuid
import re
import time
from datetime import datetime
from aiogram import Router, F, Bot
from aiogram.types import Message, CallbackQuery, FSInputFile
from aiogram.fsm.context import FSMContext
from ..states import TaskStates
from ..keyboards import cancel_keyboard, main_menu, model_keyboard, confirm_action_keyboard, running_keyboard
from ..database import Database
from ..models import Task, TaskStatus
from ..claude_client import ClaudeCodeClient
from ..notifier import TaskNotifier
from ..config import (
    CLAUDE_WORKING_DIR,
    CLAUDE_TIMEOUT,
    GLM_API_KEY,
    GLM_USE_SUBSCRIPTION,
    SYSTEM_PROMPT_FILE,
    BOT_MEMORY_DIR,
    ADMIN_IDS,
)
from ..glm_client import GLMClient
from ..memory_store import append_to_memory, load_recent_context, load_summary_context, append_summary_to_memory
from ..utils.file_sender import extract_and_send_files
from ..utils.text_formatter import strip_markdown
from ..utils.telegram_safe import safe_send_message, safe_edit_message

logger = logging.getLogger(__name__)
router = Router()

db = Database()
claude_client = ClaudeCodeClient(working_directory=CLAUDE_WORKING_DIR)
glm_client = GLMClient(api_key=GLM_API_KEY, use_subscription=GLM_USE_SUBSCRIPTION)

# Глобальные переменные
_bot: Bot = None
_notifier: TaskNotifier = None

# Хранилища
user_sessions: dict[int, str] = {}           # user_id -> session_id (кеш, восстанавливается из БД)
user_models: dict[int, str] = {}             # user_id -> model key
pending_confirmations: dict[str, dict] = {}  # confirm_id -> {user_id, task}
cancel_events: dict[str, asyncio.Event] = {} # task_id -> Event
BOT_START_TIME = time.time()

# Локальные модели (Claude CLI)
AVAILABLE_MODELS = {
    "opus":  "claude-opus-4-8",
    "sonnet": "claude-sonnet-4-6",
    "haiku":  "claude-haiku-4-5-20251001",
    "fable5": "claude-fable-5",
}
# Удалённые модели GLM
REMOTE_MODELS = {"glm4": "glm-4.7", "glm4-air": "glm-4.7-flash"}

DEFAULT_MODEL = "sonnet"
# Дефолт для админа отличается от общего — Fable 5 (дефицитная топ-модель)
ADMIN_DEFAULT_MODEL = "fable5"

DANGEROUS_PATTERNS = [
    r'\bудали\b', r'\bудалить\b', r'\bудаление\b', r'\bубери\b', r'\bубрать\b',
    r'\bdelete\b', r'\bremove\b', r'\brm\b', r'\bunlink\b', r'\berase\b',
    r'\bизмени\b', r'\bизменить\b', r'\bотредактируй\b', r'\bредактируй\b',
    r'\bпоменяй\b', r'\bзамени\b', r'\bперепиши\b', r'\bобнови\b',
    r'\bedit\b', r'\bmodify\b', r'\bchange\b', r'\bupdate\b', r'\breplace\b',
    r'\bсоздай файл\b', r'\bсоздать файл\b', r'\bнапиши в файл\b', r'\bзапиши в\b',
    r'\bcreate file\b', r'\bwrite to\b', r'\btouch\b',
    r'\bперемести\b', r'\bпереименуй\b', r'\bперенеси\b',
    r'\bmove\b', r'\brename\b', r'\bmv\b',
    r'\bformat\b', r'\bdd if\b', r'\bsudo\b', r'\bchmod\b', r'\bchown\b',
    r'\bgit push\b', r'\bgit reset\b', r'\bgit force\b',
    r'\bnpm publish\b', r'\bpip install\b',
]


def set_bot(bot: Bot):
    global _bot
    _bot = bot


def set_notifier(notifier: TaskNotifier):
    global _notifier
    _notifier = notifier


async def get_user_model(user_id: int) -> str:
    """Получить модель пользователя (кеш → БД). Для админа дефолт — Fable 5."""
    if user_id in user_models:
        return user_models[user_id]
    default = ADMIN_DEFAULT_MODEL if user_id in ADMIN_IDS else DEFAULT_MODEL
    model_key = await db.get_user_model_key(user_id, default=default)
    user_models[user_id] = model_key
    return model_key


def get_model_display_name(model_key: str) -> str:
    names = {
        "opus":     "Opus 4.8",
        "sonnet":   "Sonnet 4.6",
        "haiku":    "Haiku 4.5",
        "fable5":   "Fable 5",
        "glm4":     "GLM 4.7 (облако)",
        "glm4-air": "GLM 4.7 Flash (облако)",
    }
    return names.get(model_key, model_key)


def is_dangerous_request(text: str) -> tuple[bool, str]:
    text_lower = text.lower()
    for pattern in DANGEROUS_PATTERNS:
        if re.search(pattern, text_lower, re.IGNORECASE):
            if any(x in pattern for x in ['удал', 'delete', 'remove', 'rm', 'erase', 'убер', 'unlink']):
                return True, "удаление"
            elif any(x in pattern for x in ['измен', 'edit', 'modify', 'change', 'replace', 'помен', 'замен', 'перепиш', 'обнов', 'update', 'редакт']):
                return True, "изменение"
            elif any(x in pattern for x in ['создай', 'создать', 'create', 'write', 'touch', 'запиш', 'напиш']):
                return True, "создание"
            elif any(x in pattern for x in ['перемест', 'переимен', 'перенес', 'move', 'rename', 'mv']):
                return True, "перемещение/переименование"
            elif any(x in pattern for x in ['format', 'sudo', 'chmod', 'chown', 'git push', 'git reset']):
                return True, "системная операция"
            else:
                return True, "потенциально опасная операция"
    return False, ""


@router.message(F.text == "📝 Новая задача")
async def new_task_start(message: Message, state: FSMContext):
    await state.set_state(TaskStates.waiting_prompt)
    await message.answer("📝 Напишите вашу задачу:", reply_markup=cancel_keyboard())


@router.message(TaskStates.waiting_prompt, F.text != "❌ Отмена")
async def new_task_submit(message: Message, state: FSMContext):
    await state.clear()
    await process_task(message)


@router.message(TaskStates.waiting_prompt, F.text == "❌ Отмена")
async def cancel_task(message: Message, state: FSMContext):
    await state.clear()
    await message.answer("Отменено", reply_markup=main_menu())


@router.message(F.text == "🔄 Продолжить диалог")
async def continue_dialog(message: Message, state: FSMContext):
    user_id = message.from_user.id
    session_id = user_sessions.get(user_id) or await db.get_user_session(user_id)
    if session_id:
        await state.set_state(TaskStates.waiting_prompt)
        await message.answer("Продолжаем. Напишите:", reply_markup=cancel_keyboard())
    else:
        await message.answer("Нет активной сессии.", reply_markup=main_menu())


@router.message(F.text == "🆕 Новая сессия")
async def new_session(message: Message):
    user_id = message.from_user.id
    user_sessions.pop(user_id, None)
    await db.set_user_session(user_id, None)
    await message.answer("Сессия сброшена.", reply_markup=main_menu())


# === ВЫБОР МОДЕЛИ ===

@router.message(F.text == "🤖 Модель")
async def show_model_menu(message: Message):
    user_id = message.from_user.id
    current = await get_user_model(user_id)
    current_name = get_model_display_name(current)
    glm_available = bool(GLM_API_KEY)

    text = f"Текущая модель: **{current_name}**\n\nВыберите модель:"
    if not glm_available:
        text += "\n\n_GLM 4.7: задайте GLM_API_KEY в .env_"

    await message.answer(
        text,
        reply_markup=model_keyboard(current, glm_available=glm_available),
        parse_mode="Markdown",
    )


@router.callback_query(F.data.startswith("model_"))
async def select_model(callback: CallbackQuery):
    model_key = callback.data.replace("model_", "")

    if model_key in AVAILABLE_MODELS:
        user_models[callback.from_user.id] = model_key
        await db.set_user_model_key(callback.from_user.id, model_key)
        model_name = get_model_display_name(model_key)
        claude_client.set_model(AVAILABLE_MODELS[model_key])
        await callback.message.edit_text(f"✅ Модель: **{model_name}**", parse_mode="Markdown")
    elif model_key in REMOTE_MODELS and GLM_API_KEY:
        user_models[callback.from_user.id] = model_key
        await db.set_user_model_key(callback.from_user.id, model_key)
        model_name = get_model_display_name(model_key)
        await callback.message.edit_text(
            f"✅ Модель: **{model_name}** (удалённый API)", parse_mode="Markdown"
        )
    elif model_key in REMOTE_MODELS and not GLM_API_KEY:
        await callback.answer("Добавьте GLM_API_KEY в .env", show_alert=True)
        return

    await callback.answer()


# === ПОДТВЕРЖДЕНИЕ ОПАСНЫХ ОПЕРАЦИЙ ===

@router.callback_query(F.data.startswith("confirm_"))
async def handle_confirmation(callback: CallbackQuery):
    data = callback.data

    if data.startswith("confirm_yes_"):
        confirm_id = data.replace("confirm_yes_", "")
        if confirm_id in pending_confirmations:
            pending = pending_confirmations.pop(confirm_id)
            user_id = pending["user_id"]
            task = pending["task"]
            await callback.message.edit_text("✅ Подтверждено. Выполняю...")
            status_msg = await callback.message.answer("⏳")
            await execute_llm_task(task, user_id, status_msg)
        else:
            await callback.message.edit_text("⚠️ Запрос устарел")

    elif data.startswith("confirm_no_"):
        confirm_id = data.replace("confirm_no_", "")
        if confirm_id in pending_confirmations:
            pending = pending_confirmations.pop(confirm_id)
            await db.update_task(pending["task"].id, TaskStatus.FAILED, error="Отменено пользователем")
        await callback.message.edit_text("❌ Отменено")

    await callback.answer()


# === ОБРАБОТКА СООБЩЕНИЙ ===

@router.message(F.text)
async def direct_message(message: Message, state: FSMContext):
    menu_buttons = [
        "📝 Новая задача", "🔄 Продолжить диалог", "🆕 Новая сессия",
        "📋 Мои задачи", "⏳ Активные", "❓ Помощь", "❌ Отмена",
        "🤖 Модель", "📋 История", "ℹ️ Статус", "📂 Проекты",
    ]
    if message.text in menu_buttons:
        return
    current_state = await state.get_state()
    if current_state:
        return
    await process_task(message)


async def process_task(message: Message):
    user_id = message.from_user.id
    task_id = str(uuid.uuid4())[:8]
    task = Task(
        id=task_id,
        user_id=user_id,
        prompt=message.text,
        status=TaskStatus.PENDING,
        created_at=datetime.now(),
    )
    await db.add_task(task)

    is_dangerous, operation_type = is_dangerous_request(message.text)
    if is_dangerous:
        confirm_id = str(uuid.uuid4())[:8]
        pending_confirmations[confirm_id] = {"user_id": user_id, "task": task}
        preview = message.text[:200] + "..." if len(message.text) > 200 else message.text
        await message.answer(
            f"⚠️ **Обнаружено: {operation_type}**\n\n"
            f"```\n{preview}\n```\n\nВыполнить?",
            reply_markup=confirm_action_keyboard(confirm_id),
            parse_mode="Markdown",
        )
    else:
        status_msg = await message.answer("⏳")
        await execute_llm_task(task, user_id, status_msg)


@router.callback_query(F.data.startswith("cancel_task_"))
async def handle_cancel_task(callback: CallbackQuery):
    task_id = callback.data.replace("cancel_task_", "")
    event = cancel_events.get(task_id)
    if event:
        event.set()
        await callback.answer("Останавливаю...", show_alert=False)
        try:
            await callback.message.edit_text("🛑 Останавливаю задачу...")
        except Exception:
            pass
    else:
        await callback.answer("Задача уже завершена", show_alert=False)


async def execute_llm_task(task: Task, user_id: int, status_msg: Message):
    """Выполнить задачу (Claude или GLM) со стримингом."""
    try:
        await db.update_task(task.id, TaskStatus.RUNNING)

        # Session: кеш → БД
        session_id = user_sessions.get(user_id)
        if not session_id:
            session_id = await db.get_user_session(user_id)
            if session_id:
                user_sessions[user_id] = session_id

        model_key = await get_user_model(user_id)
        logger.info("execute_llm_task: user_id=%s model_key=%s session=%s", user_id, model_key, session_id)

        prompt = task.prompt
        if not session_id:
            if model_key in REMOTE_MODELS:
                context = load_summary_context(memory_dir=BOT_MEMORY_DIR, limit=5, max_chars=1500)
            else:
                context = load_recent_context(memory_dir=BOT_MEMORY_DIR, limit=3)
            if context:
                prompt = context + "---\nТекущий запрос: " + prompt

        if model_key in REMOTE_MODELS:
            glm_client.set_model(REMOTE_MODELS[model_key])
            if not glm_client.is_available():
                await db.update_task(task.id, TaskStatus.FAILED, error="GLM API ключ не задан")
                try:
                    await status_msg.delete()
                except Exception:
                    pass
                await safe_send_message(_bot, user_id, "❌ Добавьте GLM_API_KEY в .env", reply_markup=main_menu())
                return
            result = await glm_client.execute_task(
                prompt=prompt,
                session_id=session_id,
                timeout=CLAUDE_TIMEOUT,
            )
        else:
            model = AVAILABLE_MODELS.get(model_key, AVAILABLE_MODELS[DEFAULT_MODEL])
            claude_client.set_model(model)

            cancel_event = asyncio.Event()
            cancel_events[task.id] = cancel_event

            try:
                await status_msg.edit_text("⏳ Думаю...", reply_markup=running_keyboard(task.id))
            except Exception:
                pass

            # Раздельные буферы: инструменты и текст
            text_chunks: list[str] = []
            tool_lines: list[str] = []
            last_edit_time = [0.0]
            EDIT_INTERVAL = 0.8

            async def on_chunk(text: str):
                if text.startswith("\x00"):
                    # Маркер события tool_use
                    tool_lines.append(text[1:])
                else:
                    text_chunks.append(text)

                now = asyncio.get_event_loop().time()
                if now - last_edit_time[0] >= EDIT_INTERVAL:
                    last_edit_time[0] = now
                    recent_tools = "\n".join(tool_lines[-2:]) if tool_lines else ""
                    recent_text = strip_markdown("".join(text_chunks))[-2800:]
                    if recent_tools:
                        preview = recent_tools + "\n" + recent_text
                    else:
                        preview = recent_text
                    preview = preview[-3800:]
                    try:
                        await safe_edit_message(
                            status_msg,
                            f"⏳ {preview}…" if preview else "⏳ Думаю...",
                            reply_markup=running_keyboard(task.id),
                        )
                    except Exception:
                        pass

            result = await claude_client.execute_task_streaming(
                prompt=prompt,
                session_id=session_id,
                on_chunk=on_chunk,
                system_prompt_file=SYSTEM_PROMPT_FILE,
                memory_dir=BOT_MEMORY_DIR,
                cancel_event=cancel_event,
            )

            cancel_events.pop(task.id, None)

        try:
            await status_msg.delete()
        except Exception:
            pass

        if result.get("cancelled"):
            partial = result.get("result", "")
            await db.update_task(task.id, TaskStatus.FAILED, error="Остановлено пользователем")
            if partial:
                await safe_send_message(
                    _bot, user_id,
                    f"🛑 Остановлено.\n\n{strip_markdown(partial[:3000])}",
                    reply_markup=main_menu(),
                )
            else:
                await safe_send_message(_bot, user_id, "🛑 Задача остановлена.", reply_markup=main_menu())
            return

        if result.get("success"):
            new_session_id = result.get("session_id")
            if new_session_id and model_key not in REMOTE_MODELS:
                user_sessions[user_id] = new_session_id
                await db.set_user_session(user_id, new_session_id)

            response_text = result.get("result", "")
            await db.update_task(task.id, TaskStatus.COMPLETED, result=response_text)

            await send_result(user_id, response_text, model_key=model_key)

            append_to_memory(
                created_at=task.created_at,
                model_display=get_model_display_name(model_key),
                prompt=task.prompt,
                result=response_text,
            )

            try:
                summary = await glm_client.generate_summary(
                    prompt=task.prompt, response=response_text, timeout=30,
                )
                if summary:
                    append_summary_to_memory(
                        summary=summary, created_at=task.created_at, memory_dir=BOT_MEMORY_DIR,
                    )
            except Exception as e:
                logger.debug("Summary generation skipped: %s", e)
        else:
            error_msg = result.get("error", "Ошибка")
            await db.update_task(task.id, TaskStatus.FAILED, error=error_msg)

            current_model = await get_user_model(user_id)
            if current_model in REMOTE_MODELS and model_key not in REMOTE_MODELS:
                logger.info("Пропуск ошибки Claude для user %s (сейчас %s)", user_id, current_model)
            elif any(s in error_msg.lower() for s in ("usage limit", "rate limit", "rate_limit", "limit reached")):
                await safe_send_message(_bot, user_id, "⏸️ Лимит исчерпан.", reply_markup=main_menu())
            elif "timeout" in error_msg.lower():
                await safe_send_message(_bot, user_id, "⏱️ Таймаут.", reply_markup=main_menu())
            else:
                await safe_send_message(_bot, user_id, f"❌ {error_msg}", reply_markup=main_menu())

    except Exception as e:
        logger.exception("Ошибка execute_llm_task: %s", e)
        await db.update_task(task.id, TaskStatus.FAILED, error=str(e))
        cancel_events.pop(task.id, None)
        try:
            await status_msg.delete()
        except Exception:
            pass
        await safe_send_message(_bot, user_id, "❌ Ошибка.", reply_markup=main_menu())


async def send_result(user_id: int, result: str, model_key: str = ""):
    """Отправить результат: текст (≤3500 символов) или .md файл."""
    if not _bot:
        return

    cleaned_result = strip_markdown(result)

    if len(cleaned_result) <= 3500:
        await safe_send_message(_bot, user_id, cleaned_result, reply_markup=main_menu())
    else:
        os.makedirs("/tmp/claude_bot/output", exist_ok=True)
        ts = int(time.time())
        file_path = f"/tmp/claude_bot/output/response_{user_id}_{ts}.md"
        try:
            with open(file_path, "w", encoding="utf-8") as f:
                f.write(result)
            doc = FSInputFile(file_path, filename=f"response_{ts}.md")
            await _bot.send_document(
                user_id,
                doc,
                caption=f"📄 Ответ Claude ({len(cleaned_result)} симв.)",
                reply_markup=main_menu(),
            )
        except Exception as e:
            logger.error("Не удалось отправить документ: %s", e)
            await safe_send_message(
                _bot, user_id,
                cleaned_result[:3500] + "\n…(обрезано)",
                reply_markup=main_menu(),
            )
        finally:
            try:
                os.remove(file_path)
            except OSError:
                pass

    await extract_and_send_files(_bot, user_id, result)


def split_message(text: str, max_length: int) -> list[str]:
    chunks = []
    while text:
        if len(text) <= max_length:
            chunks.append(text)
            break
        split_at = max_length
        newline_pos = text.rfind('\n', 0, max_length)
        if newline_pos > max_length // 2:
            split_at = newline_pos + 1
        chunks.append(text[:split_at])
        text = text[split_at:]
    return chunks
