import logging
from aiogram import Router, F
from aiogram.types import Message
from aiogram.filters import CommandStart, Command
from aiogram.fsm.context import FSMContext
from ..keyboards import main_menu
from ..database import Database

logger = logging.getLogger(__name__)
router = Router()

db = Database()


@router.message(CommandStart())
async def start_command(message: Message, state: FSMContext):
    """Команда /start"""
    await state.clear()

    # Добавить пользователя в БД
    db.add_user(message.from_user.id, message.from_user.username)

    welcome_text = (
        "👋 Привет! Я Claude Code Assistant.\n\n"
        "Просто напиши мне сообщение — я передам его Claude.\n\n"
        "🤖 Модель — выбрать Opus/Sonnet/Haiku\n"
        "🆕 Новая сессия — начать заново"
    )

    await message.answer(welcome_text, reply_markup=main_menu())


@router.message(Command("help"))
async def help_command(message: Message):
    """Команда /help"""
    help_text = (
        "Просто напиши сообщение — Claude ответит.\n\n"
        "🤖 Модель — сменить модель\n"
        "🆕 Новая сессия — сбросить контекст\n"
        "/status — проверить статус"
    )
    await message.answer(help_text, reply_markup=main_menu())


@router.message(F.text == "❓ Помощь")
async def help_button(message: Message):
    """Кнопка помощь"""
    await help_command(message)
