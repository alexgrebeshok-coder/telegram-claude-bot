from aiogram.types import ReplyKeyboardMarkup, KeyboardButton, InlineKeyboardMarkup, InlineKeyboardButton


def main_menu() -> ReplyKeyboardMarkup:
    """Главное меню"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="🆕 Новая сессия"), KeyboardButton(text="🤖 Модель")],
        ],
        resize_keyboard=True
    )


def cancel_keyboard() -> ReplyKeyboardMarkup:
    """Клавиатура отмены"""
    return ReplyKeyboardMarkup(
        keyboard=[
            [KeyboardButton(text="❌ Отмена")],
        ],
        resize_keyboard=True
    )


def model_keyboard(current_model: str = "sonnet") -> InlineKeyboardMarkup:
    """Клавиатура выбора модели"""
    models = [
        ("opus", "Opus 4.5", "🧠"),
        ("sonnet", "Sonnet 4.5", "⚡"),
        ("haiku", "Haiku 4.5", "🚀"),
    ]
    
    buttons = []
    for key, name, emoji in models:
        check = " ✓" if key == current_model else ""
        buttons.append([
            InlineKeyboardButton(
                text=f"{emoji} {name}{check}",
                callback_data=f"model_{key}"
            )
        ])
    
    return InlineKeyboardMarkup(inline_keyboard=buttons)


def tasks_menu() -> InlineKeyboardMarkup:
    """Меню для задач"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="🔄 Обновить", callback_data="refresh_tasks")],
            [InlineKeyboardButton(text="❌ Закрыть", callback_data="close_menu")],
        ]
    )


def task_detail_menu(task_id: str) -> InlineKeyboardMarkup:
    """Меню деталей задачи"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [InlineKeyboardButton(text="📄 Полный результат", callback_data=f"full_result_{task_id}")],
            [InlineKeyboardButton(text="⬅️ Назад", callback_data="back_to_tasks")],
        ]
    )


def confirm_keyboard() -> InlineKeyboardMarkup:
    """Подтверждение"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Да", callback_data="confirm_yes"),
                InlineKeyboardButton(text="❌ Нет", callback_data="confirm_no"),
            ]
        ]
    )


def confirm_action_keyboard(confirm_id: str) -> InlineKeyboardMarkup:
    """Подтверждение опасного действия"""
    return InlineKeyboardMarkup(
        inline_keyboard=[
            [
                InlineKeyboardButton(text="✅ Выполнить", callback_data=f"confirm_yes_{confirm_id}"),
                InlineKeyboardButton(text="❌ Отмена", callback_data=f"confirm_no_{confirm_id}"),
            ]
        ]
    )
