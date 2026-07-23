import logging
from aiogram import Bot
from .database import Database
from .models import TaskStatus

logger = logging.getLogger(__name__)


class TaskNotifier:
    """Отправляет уведомления пользователям о статусе задач"""

    def __init__(self, bot: Bot):
        self.bot = bot
        self.db = Database()

    async def notify_task_completed(self, task_id: str):
        """Отправить уведомление о завершении задачи"""
        task = await self.db.get_task(task_id)
        if not task:
            return

        if task.status != TaskStatus.COMPLETED:
            return

        message_text = (
            f"✅ Ваша задача выполнена!\n\n"
            f"ID задачи: {task.id}\n"
            f"Задача: {task.prompt[:100]}...\n\n"
        )

        if task.result:
            # Если результат короткий, показать его сразу
            if len(task.result) < 500:
                message_text += f"Результат:\n{task.result}"
            else:
                message_text += "Результат готов (длинный результат)\nИспользуйте команду '📋 Мои задачи' для просмотра"
        else:
            message_text += "Результат готов, но текст не сохранён"

        try:
            await self.bot.send_message(
                chat_id=task.user_id,
                text=message_text,
                parse_mode="HTML"
            )
            logger.info(f"Уведомление отправлено пользователю {task.user_id} о задаче {task.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления: {e}")

    async def notify_task_failed(self, task_id: str):
        """Отправить уведомление об ошибке при выполнении задачи"""
        task = await self.db.get_task(task_id)
        if not task:
            return

        if task.status != TaskStatus.FAILED:
            return

        error_body = task.error or "Неизвестная ошибка"
        connection_hint = ""
        if "Cannot connect" in error_body or "Connect call failed" in error_body:
            connection_hint = (
                "\n\n💡 Убедитесь, что Claude Code запущен: в первом терминале выполните «claude code» "
                "и дождитесь сообщения о запуске на http://127.0.0.1:5173"
            )
        message_text = (
            f"❌ Ошибка при выполнении задачи\n\n"
            f"ID задачи: {task.id}\n"
            f"Задача: {task.prompt[:100]}...\n\n"
            f"Ошибка:\n{error_body}{connection_hint}"
        )

        try:
            await self.bot.send_message(
                chat_id=task.user_id,
                text=message_text,
                parse_mode="HTML"
            )
            logger.info(f"Уведомление об ошибке отправлено пользователю {task.user_id} о задаче {task.id}")
        except Exception as e:
            logger.error(f"Ошибка отправки уведомления об ошибке: {e}")
