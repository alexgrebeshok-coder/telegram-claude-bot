import logging
import asyncio
import shutil
from aiogram import Router, F
from aiogram.types import Message, CallbackQuery
from aiogram.filters import Command
from aiogram.fsm.context import FSMContext
from ..keyboards import main_menu, tasks_menu, task_detail_menu
from ..database import Database
from ..config import CLAUDE_WORKING_DIR

logger = logging.getLogger(__name__)
router = Router()

db = Database()


def format_task_status(status: str) -> str:
    """Форматировать статус задачи в эмодзи"""
    status_map = {
        "pending": "⏳ Ожидание",
        "running": "🔄 Выполняется",
        "completed": "✅ Завершено",
        "failed": "❌ Ошибка"
    }
    return status_map.get(status, status)


@router.message(F.text == "📋 Мои задачи")
async def my_tasks(message: Message, state: FSMContext):
    """Показать задачи пользователя"""
    await state.clear()

    tasks = db.get_user_tasks(message.from_user.id, limit=10)

    if not tasks:
        await message.answer(
            "📭 У вас нет задач\n\n"
            "Создайте новую задачу кнопкой '📝 Новая задача'",
            reply_markup=main_menu()
        )
        return

    # Форматировать список задач
    tasks_text = "📋 Ваши последние задачи:\n\n"
    for i, task in enumerate(tasks, 1):
        status_emoji = format_task_status(task.status.value)
        tasks_text += (
            f"{i}. {status_emoji}\n"
            f"   ID: {task.id}\n"
            f"   Задача: {task.prompt[:50]}...\n"
            f"   Создано: {task.created_at.strftime('%d.%m %H:%M')}\n\n"
        )

    await message.answer(tasks_text, reply_markup=tasks_menu())


@router.message(F.text == "⏳ Активные")
async def active_tasks(message: Message, state: FSMContext):
    """Показать активные задачи"""
    await state.clear()

    tasks = db.get_pending_tasks()

    if not tasks:
        await message.answer(
            "✨ Все задачи завершены!",
            reply_markup=main_menu()
        )
        return

    # Форматировать список активных задач
    tasks_text = "⏳ Активные задачи:\n\n"
    for i, task in enumerate(tasks, 1):
        status_emoji = format_task_status(task.status.value)
        tasks_text += (
            f"{i}. {status_emoji}\n"
            f"   ID: {task.id}\n"
            f"   Задача: {task.prompt[:50]}...\n"
            f"   Статус: {task.status.value}\n\n"
        )

    await message.answer(tasks_text, reply_markup=tasks_menu())


@router.callback_query(F.data == "refresh_tasks")
async def refresh_tasks(callback: CallbackQuery):
    """Обновить список задач"""
    tasks = db.get_user_tasks(callback.from_user.id, limit=10)

    if not tasks:
        await callback.answer("У вас нет задач", show_alert=True)
        return

    tasks_text = "📋 Ваши последние задачи:\n\n"
    for i, task in enumerate(tasks, 1):
        status_emoji = format_task_status(task.status.value)
        tasks_text += (
            f"{i}. {status_emoji}\n"
            f"   ID: {task.id}\n"
            f"   Задача: {task.prompt[:50]}...\n"
            f"   Создано: {task.created_at.strftime('%d.%m %H:%M')}\n\n"
        )

    await callback.message.edit_text(tasks_text, reply_markup=tasks_menu())
    await callback.answer()


@router.callback_query(F.data == "close_menu")
async def close_menu(callback: CallbackQuery):
    """Закрыть меню"""
    await callback.message.delete()
    await callback.answer()


@router.callback_query(F.data.startswith("full_result_"))
async def show_full_result(callback: CallbackQuery):
    """Показать полный результат задачи"""
    task_id = callback.data.split("_")[-1]
    task = db.get_task(task_id)

    if not task:
        await callback.answer("Задача не найдена", show_alert=True)
        return

    if task.status.value == "completed" and task.result:
        result_text = f"📄 Полный результат (ID: {task.id})\n\n{task.result}"
        # Отправить как новое сообщение если результат длинный
        if len(result_text) > 4096:
            # Разбить на части
            for i in range(0, len(result_text), 4096):
                await callback.message.answer(result_text[i:i+4096])
        else:
            await callback.answer(result_text, show_alert=True)
    else:
        await callback.answer(f"Результат ещё не готов (статус: {task.status.value})", show_alert=True)


@router.message(Command("status"))
async def status_command(message: Message):
    """Показать статус системы"""
    status_parts = ["📊 **Статус системы**\n"]
    
    # Проверить Claude CLI
    claude_path = shutil.which("claude")
    if claude_path:
        try:
            proc = await asyncio.create_subprocess_exec(
                claude_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(proc.communicate(), timeout=5)
            version = stdout.decode().strip()
            status_parts.append(f"✅ Claude CLI: {version}")
        except Exception as e:
            status_parts.append(f"⚠️ Claude CLI: ошибка ({e})")
    else:
        status_parts.append("❌ Claude CLI: не найден")
    
    # Рабочая директория
    status_parts.append(f"📁 Рабочая папка: `{CLAUDE_WORKING_DIR}`")
    
    # Статистика задач
    pending = db.get_pending_tasks()
    user_tasks = db.get_user_tasks(message.from_user.id, limit=100)
    completed = sum(1 for t in user_tasks if t.status.value == "completed")
    failed = sum(1 for t in user_tasks if t.status.value == "failed")
    
    status_parts.append(f"\n📈 **Статистика:**")
    status_parts.append(f"• Активных задач: {len(pending)}")
    status_parts.append(f"• Выполнено: {completed}")
    status_parts.append(f"• Ошибок: {failed}")
    
    # Бот работает
    status_parts.append(f"\n🤖 Бот: работает")
    
    await message.answer(
        "\n".join(status_parts),
        reply_markup=main_menu(),
        parse_mode="Markdown"
    )
