import asyncio
import logging
from typing import Optional

logger = logging.getLogger(__name__)


async def safe_edit_message(message, text: str, reply_markup=None, max_retries: int = 3, **kwargs):
    """Edit message with automatic retry on Telegram rate limit (429)."""
    from aiogram.exceptions import TelegramRetryAfter, TelegramBadRequest
    for attempt in range(max_retries):
        try:
            await message.edit_text(text, reply_markup=reply_markup, **kwargs)
            return
        except TelegramRetryAfter as e:
            if attempt < max_retries - 1:
                logger.debug("Rate limit on edit, sleeping %ss", e.retry_after)
                await asyncio.sleep(e.retry_after + 0.1)
            else:
                logger.warning("Rate limit hit %d times on edit, giving up", max_retries)
        except TelegramBadRequest:
            # Message not modified or deleted — not an error
            return
        except Exception:
            return


async def safe_send_message(bot, chat_id: int, text: str, reply_markup=None, max_retries: int = 3, **kwargs):
    """Send message with automatic retry on Telegram rate limit (429)."""
    from aiogram.exceptions import TelegramRetryAfter
    for attempt in range(max_retries):
        try:
            return await bot.send_message(chat_id, text, reply_markup=reply_markup, **kwargs)
        except TelegramRetryAfter as e:
            if attempt < max_retries - 1:
                logger.debug("Rate limit on send, sleeping %ss", e.retry_after)
                await asyncio.sleep(e.retry_after + 0.1)
            else:
                logger.warning("Rate limit hit %d times on send, giving up", max_retries)
        except Exception as e:
            logger.debug("send_message failed: %s", e)
            return None
    return None
