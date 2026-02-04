"""
Клиент для GLM-4.7 через Zhipu AI API (удалённый).
Поддерживает два режима:
- Подписка (Coding API, api.z.ai) — квота Pro/Forward, без отдельной оплаты.
- Баланс (open.bigmodel.cn) — списание с 余额/资源包.
Контракт совместим с ClaudeCodeClient.execute_task (success, result, session_id).
"""
import logging
import os
from typing import Optional, Dict, Any

import aiohttp

# Таймаут установки соединения (отдельно от total), чтобы не ждать 600s при недоступном API
GLM_CONNECT_TIMEOUT = int(os.getenv("GLM_CONNECT_TIMEOUT", "60"))

logger = logging.getLogger(__name__)

# Coding API (подписка Z.AI Coding Plan) — dedicated endpoint для подписки
URL_CODING_API = "https://api.z.ai/api/coding/paas/v4/chat/completions"
# General API (open.bigmodel.cn) — баланс/资源包
URL_OPEN_PLATFORM = "https://open.bigmodel.cn/api/paas/v4/chat/completions"
# Модели GLM-4.7 для Z.AI Coding API
GLM_MODEL_DEFAULT = "glm-4.7"

# Системный промпт для Telegram (согласован с system_prompt.md для Claude Code)
GLM_SYSTEM_PROMPT = """Ты — умный и полезный ИИ-ассистент, интегрированный в Telegram-бота. Твоя задача — помогать пользователю быстро и эффективно. Действуй сразу: если просят сделать что-то — делай, потом кратко отчитайся. После задачи — краткий итог: что сделано.

СТРОГИЕ ПРАВИЛА ФОРМАТИРОВАНИЯ И СТИЛЯ:
Краткость — сестра таланта: Telegram используется в основном на мобильных устройствах. Избегай "воды" и долгих вступлений. Отвечай конкретно по существу. Если ответ получается очень длинным, разбей его на логические части с абзацами.
Визуальная структура: Обязательно используй Markdown для оформления, чтобы текст легко сканировался глазами:
   • Используй жирный шрифт для заголовков, ключевых терминов и важной информации.
   • Используй курсив для акцентов или выделения примеров.
   • Используй код в кавычках для названий команд, файлов или технических терминов.
   • Для списков используй буллиты (точки) или нумерацию.
   • Никогда не пиши "простыню" текста без переносов строк.
Стиль общения: Будь дружелюбным, но профессиональным. Не будь слишком душным или роботизированным. Адаптируйся под тон пользователя, но сохраняй полезность.
Формат кода: Если нужно показать код или длинный фрагмент текста, используй тройные обратные кавычки, но только если это действительно необходимо. Для коротких команд используй inline-код.
Язык: Всегда отвечай на том языке, на котором тебе написал пользователь (если это не запрос на перевод).

Контекст: Если в запросе есть блок [Контекст из предыдущих сессий] — учти его при ответе.

Твоя главная цель — стать самым удобным ассистентом для пользователя в мессенджере."""


class GLMClient:
    """Клиент для вызова GLM через Zhipu AI API (удалённо)."""

    def __init__(
        self,
        api_key: Optional[str] = None,
        use_subscription: bool = True,
    ):
        self.api_key = api_key
        self.model = GLM_MODEL_DEFAULT
        self.chat_url = URL_CODING_API if use_subscription else URL_OPEN_PLATFORM
        if use_subscription:
            logger.info("GLM: использование Coding API (подписка Z.AI)")
        else:
            logger.info("GLM: использование open.bigmodel.cn (баланс/资源包)")

    async def generate_summary(
        self,
        prompt: str,
        response: str,
        timeout: int = 30,
    ) -> str:
        """
        Сгенерировать краткое summary диалога (1-2 предложения).
        Используется для компактного контекста в будущих запросах.
        """
        if not self.api_key:
            return ""

        # Обрезаем входные данные, если слишком длинные
        prompt_short = prompt[:500] + "..." if len(prompt) > 500 else prompt
        response_short = response[:1000] + "..." if len(response) > 1000 else response

        summary_prompt = f"""Сделай ОЧЕНЬ краткое summary диалога (1-2 предложения, максимум 150 символов).
Формат: "Пользователь [что хотел]. Результат: [что получилось]."

Запрос пользователя:
{prompt_short}

Ответ ассистента:
{response_short}

Summary:"""

        payload = {
            "model": "glm-4.7-flash",  # Используем быструю модель для summary
            "messages": [
                {"role": "user", "content": summary_prompt},
            ],
            "max_tokens": 100,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(connect=15, total=timeout),
                ) as resp:
                    if resp.status != 200:
                        logger.warning("GLM summary error: %s", resp.status)
                        return ""
                    data = await resp.json()

            choices = data.get("choices") or []
            if not choices:
                return ""

            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            return content.strip()[:200]  # Ограничиваем длину summary

        except Exception as e:
            logger.warning("GLM summary generation failed: %s", e)
            return ""

    def set_api_key(self, api_key: Optional[str]) -> None:
        self.api_key = api_key

    def set_model(self, model: str) -> None:
        """Установить модель (например glm-4.7, glm-4.7-flash)."""
        self.model = model

    def is_available(self) -> bool:
        """Проверить, настроен ли API ключ."""
        return bool(self.api_key)

    async def execute_task(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300,
    ) -> Dict[str, Any]:
        """
        Выполнить запрос к GLM API.
        session_id не используется (каждый запрос без истории).
        Возвращает тот же формат, что ClaudeCodeClient: success, result, session_id.
        """
        if not self.api_key:
            return {
                "success": False,
                "error": "GLM API ключ не задан. Добавьте GLM_API_KEY в .env",
                "session_id": session_id,
            }

        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": GLM_SYSTEM_PROMPT},
                {"role": "user", "content": prompt},
            ],
            "max_tokens": 4096,
        }

        headers = {
            "Authorization": f"Bearer {self.api_key}",
            "Content-Type": "application/json",
        }

        try:
            logger.info("GLM request to %s model=%s", self.chat_url, self.model)
            async with aiohttp.ClientSession() as session:
                async with session.post(
                    self.chat_url,
                    json=payload,
                    headers=headers,
                    timeout=aiohttp.ClientTimeout(connect=GLM_CONNECT_TIMEOUT, total=timeout),
                ) as resp:
                    logger.info("GLM response status=%s", resp.status)
                    data = await resp.json()

            if resp.status != 200:
                err_msg = data.get("error", {}).get("message", data.get("message", str(data)))
                logger.warning("GLM API error %s: %s", resp.status, err_msg)
                return {
                    "success": False,
                    "error": f"GLM API: {err_msg}",
                    "session_id": session_id,
                }

            # OpenAI-совместимый ответ: choices[0].message.content
            choices = data.get("choices") or []
            if not choices:
                return {
                    "success": False,
                    "error": "GLM API: пустой ответ",
                    "session_id": session_id,
                }

            message = choices[0].get("message") or {}
            content = message.get("content") or ""
            if isinstance(content, list):
                content = "".join(
                    c.get("text", "") if isinstance(c, dict) else str(c) for c in content
                )

            return {
                "success": True,
                "result": content.strip(),
                "session_id": session_id,
            }

        except aiohttp.ClientError as e:
            logger.exception("GLM API request failed: %s", e)
            return {
                "success": False,
                "error": f"Ошибка сети: {e}",
                "session_id": session_id,
            }
        except Exception as e:
            logger.exception("GLM error: %s", e)
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id,
            }
