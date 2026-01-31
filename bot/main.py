import asyncio
import logging
from aiogram import Dispatcher, Bot
from aiogram.fsm.storage.memory import MemoryStorage
from aiogram.types import BotCommand, BotCommandScopeDefault

from .config import BOT_TOKEN
from .handlers import commands, tasks, management, media
from .notifier import TaskNotifier

# Настройка логирования
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    handlers=[
        logging.FileHandler('bot.log'),
        logging.StreamHandler()
    ]
)

logger = logging.getLogger(__name__)


async def set_commands(bot: Bot):
    """Установить команды бота"""
    bot_commands = [
        BotCommand(command="start", description="Начать работу"),
        BotCommand(command="help", description="Справка"),
        BotCommand(command="status", description="Статус системы"),
    ]
    await bot.set_my_commands(bot_commands, BotCommandScopeDefault())


async def main():
    """Запуск бота"""
    logger.info("Запуск Claude Code Assistant Bot...")

    # Инициализация
    bot = Bot(token=BOT_TOKEN)
    storage = MemoryStorage()
    dp = Dispatcher(storage=storage)

    # Инициализировать notifier и передать в handlers
    notifier = TaskNotifier(bot)
    tasks.set_bot(bot)
    tasks.set_notifier(notifier)

    # Регистрация роутеров
    dp.include_router(commands.router)
    dp.include_router(media.router)  # До tasks.router — приоритет для медиа
    dp.include_router(tasks.router)
    dp.include_router(management.router)

    # Установить команды
    await set_commands(bot)

    # Очистить вебхуки (на случай если использовались)
    await bot.delete_webhook(drop_pending_updates=True)

    logger.info("Бот успешно запущен и готов к работе!")
    logger.info("Используется polling для получения обновлений")

    # Запустить polling
    try:
        await dp.start_polling(bot, allowed_updates=dp.resolve_used_update_types())
    except KeyboardInterrupt:
        logger.info("Бот остановлен пользователем")
    finally:
        await bot.session.close()
        logger.info("Сессия бота закрыта")


if __name__ == "__main__":
    asyncio.run(main())
