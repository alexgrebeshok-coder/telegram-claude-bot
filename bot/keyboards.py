from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton
from typing import List


def main_menu() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Новая сессия"), KeyboardButton(text="🤖 Модель")],
            [KeyboardButton(text="📂 Проекты"),      KeyboardButton(text="ℹ️ Статус")],
            [KeyboardButton(text="📋 История"),      KeyboardButton(text="❓ Помощь")],
        ],
        resize_keyboard=True,
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    return ReplyKeyboardMarkup(
        keyboard=[[KeyboardButton(text="❌ Отмена")]],
        resize_keyboard=True,
    )


def running_keyboard(task_id: str) -> InlineKeyboardMarkup:
    """Кнопка отмены во время выполнения задачи."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="🛑 Остановить", callback_data=f"cancel_task_{task_id}"),
        ]]
    )


def model_keyboard(
    current_model: str = "sonnet",
    glm_available: bool = False,
) -> InlineKeyboardMarkup:
    models = [
        ("opus",     "Opus 4.8",         "🧠"),
        ("sonnet",   "Sonnet 4.6",       "⚡"),
        ("haiku",    "Haiku 4.5",        "🚀"),
        ("fable5",   "Fable 5",          "📖"),
        ("glm4",     "GLM 4.7 (облако)", "🌐"),
        ("glm4-air", "GLM 4.7 Flash",    "☁️"),
    ]
    buttons = []
    for key, name, emoji in models:
        check = " ✓" if key == current_model else ""
        buttons.append([InlineKeyboardButton(
            text=f"{emoji} {name}{check}",
            callback_data=f"model_{key}",
        )])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def projects_keyboard(dirs: List[str]) -> InlineKeyboardMarkup:
    """Inline-клавиатура для выбора проекта из QUICK_DIRS."""
    if not dirs:
        return InlineKeyboardMarkup(inline_keyboard=[[
            InlineKeyboardButton(text="(не настроено — добавьте QUICK_DIRS в .env)", callback_data="proj_none"),
        ]])
    buttons = []
    for d in dirs:
        label = f"📂 {d.rstrip('/').split('/')[-1]}"
        buttons.append([InlineKeyboardButton(text=label, callback_data=f"proj_{d}")])
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tasks_menu() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks")],
            [InlineKeyboardButton(text="❌ Закрыть",  callback_data="close_menu")],
        ]
    )


def task_detail_menu(task_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Полный результат", callback_data=f"full_result_{task_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_tasks")],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Да",  callback_data="confirm_yes"),
            InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no"),
        ]]
    )


def confirm_action_keyboard(confirm_id: str) -> InlineKeyboardMarkup:
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Выполнить", callback_data=f"confirm_yes_{confirm_id}"),
            InlineKeyboardButton(text="❌ Отмена",    callback_data=f"confirm_no_{confirm_id}"),
        ]]
    )


def run_confirm_keyboard(confirm_id: str) -> InlineKeyboardMarkup:
    """Подтверждение для /run команды."""
    return InlineKeyboardMarkup(
        inline_keyboard=[[
            InlineKeyboardButton(text="✅ Выполнить", callback_data=f"run_yes_{confirm_id}"),
            InlineKeyboardButton(text="❌ Отмена",    callback_data=f"run_no_{confirm_id}"),
        ]]
    )
