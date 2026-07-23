import asyncio
import json
import logging
import os
import shutil
from typing import Optional, Dict, Any, Callable

logger = logging.getLogger(__name__)


class ClaudeCodeClient:
    """Клиент для запуска Claude Code CLI локально через subprocess"""

    def __init__(self, working_directory: Optional[str] = None, model: Optional[str] = None):
        """
        Инициализация клиента
        
        Args:
            working_directory: Рабочая директория для Claude Code.
            model: Модель Claude (например claude-sonnet-4-5-20250929)
        """
        self.working_directory = working_directory or os.path.expanduser("~")
        self.claude_path = self._find_claude_binary()
        self.current_session_id: Optional[str] = None
        self.model: Optional[str] = model
    
    def set_model(self, model: str):
        """Установить модель"""
        self.model = model
        logger.info(f"Модель установлена: {model}")
        
    def _find_claude_binary(self) -> str:
        """Найти путь к claude CLI"""
        # Проверяем стандартные места
        claude_path = shutil.which("claude")
        if claude_path:
            return claude_path
        
        # Проверяем типичные пути установки
        possible_paths = [
            "/usr/local/bin/claude",
            os.path.expanduser("~/.claude/bin/claude"),
            os.path.expanduser("~/.local/bin/claude"),
        ]
        
        for path in possible_paths:
            if os.path.isfile(path) and os.access(path, os.X_OK):
                return path
        
        # Если не нашли, вернём "claude" и надеемся что он в PATH
        return "claude"

    async def execute_task(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        timeout: int = 300,
        system_prompt_file: Optional[str] = None,
        memory_dir: Optional[str] = None,
    ) -> Dict[str, Any]:
        """
        Выполнить задачу через Claude Code CLI

        Args:
            prompt: Текст задачи
            session_id: ID сессии для продолжения (опционально)
            timeout: Таймаут в секундах (по умолчанию 5 минут)
            system_prompt_file: Путь к файлу с доп. системным промптом (append)
            memory_dir: Директория памяти — добавляется в --add-dir для доступа Claude

        Returns:
            Результат выполнения с полями success, result, session_id
        """
        try:
            # Формируем команду
            cmd = [
                self.claude_path,
                "-p",  # Print mode — неинтерактивный
                "--dangerously-skip-permissions",  # Без подтверждений
                "--output-format", "json",  # JSON вывод
                "--add-dir", self.working_directory,  # Доступ к рабочей директории
            ]

            # Директория памяти — чтобы Claude мог читать логи
            if memory_dir and os.path.isdir(memory_dir):
                cmd.extend(["--add-dir", memory_dir])

            # Модель
            if self.model:
                cmd.extend(["--model", self.model])

            # Системный промпт (append к дефолтному)
            if system_prompt_file and os.path.isfile(system_prompt_file):
                cmd.extend(["--append-system-prompt-file", os.path.abspath(system_prompt_file)])
                logger.debug("Используется system prompt: %s", system_prompt_file)

            # Если есть сессия — продолжаем её
            if session_id:
                cmd.extend(["--resume", session_id])

            # Добавляем промпт
            cmd.append(prompt)
            
            logger.info(f"Запуск Claude CLI: {' '.join(cmd[:4])}... '{prompt[:50]}...'")
            
            # Запускаем процесс
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory
            )
            
            try:
                stdout, stderr = await asyncio.wait_for(
                    process.communicate(),
                    timeout=timeout
                )
            except asyncio.TimeoutError:
                process.kill()
                await process.wait()
                logger.error(f"Timeout при выполнении задачи ({timeout}s)")
                return {
                    "success": False,
                    "error": f"Timeout: задача выполнялась более {timeout} секунд",
                    "session_id": session_id
                }
            
            stdout_text = stdout.decode("utf-8", errors="replace")
            stderr_text = stderr.decode("utf-8", errors="replace")
            
            if process.returncode != 0:
                # stderr часто пустой; выводим и stdout для диагностики
                err_detail = stderr_text.strip() or stdout_text.strip()[:500] or f"код выхода {process.returncode}"
                logger.error(
                    "Claude CLI ошибка (код %s): stderr=%r stdout_head=%r",
                    process.returncode,
                    stderr_text[:500] if stderr_text else "",
                    stdout_text[:500] if stdout_text else "",
                )
                return {
                    "success": False,
                    "error": f"Claude Code ошибка: {err_detail}",
                    "session_id": session_id
                }
            
            # Парсим JSON ответ
            try:
                result = json.loads(stdout_text)
                
                # Извлекаем session_id из результата если есть
                new_session_id = result.get("session_id") or session_id
                self.current_session_id = new_session_id
                
                # Извлекаем текстовый ответ
                response_text = self._extract_response(result)
                
                logger.info(f"Задача выполнена успешно, сессия: {new_session_id}")
                
                return {
                    "success": True,
                    "result": response_text,
                    "raw_result": result,
                    "session_id": new_session_id
                }
                
            except json.JSONDecodeError:
                # Если не JSON — возвращаем как текст
                logger.warning("Ответ не в JSON формате, возвращаем как текст")
                return {
                    "success": True,
                    "result": stdout_text,
                    "session_id": session_id
                }
                
        except FileNotFoundError:
            logger.error(f"Claude CLI не найден: {self.claude_path}")
            return {
                "success": False,
                "error": "Claude Code CLI не найден. Убедитесь что он установлен и доступен в PATH.",
                "session_id": None
            }
        except Exception as e:
            logger.error(f"Ошибка при выполнении задачи: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }

    def _extract_response(self, result: Dict[str, Any]) -> str:
        """Извлечь текстовый ответ из JSON результата Claude"""
        # Структура ответа может варьироваться
        # Пробуем разные варианты
        
        if isinstance(result, str):
            return result
        
        # Стандартный формат с result
        if "result" in result:
            return result["result"]
        
        # Формат с content блоками
        if "content" in result:
            content = result["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                texts = []
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        texts.append(block.get("text", ""))
                    elif isinstance(block, str):
                        texts.append(block)
                return "\n".join(texts)
        
        # Формат с message
        if "message" in result:
            return result["message"]
        
        # Формат с output
        if "output" in result:
            return result["output"]
        
        # Если ничего не подошло — возвращаем весь JSON
        return json.dumps(result, ensure_ascii=False, indent=2)

    async def execute_task_streaming(
        self,
        prompt: str,
        session_id: Optional[str] = None,
        on_chunk: Optional[Callable] = None,
        system_prompt_file: Optional[str] = None,
        memory_dir: Optional[str] = None,
        cancel_event: Optional[asyncio.Event] = None,
    ) -> Dict[str, Any]:
        """
        Выполнить задачу со стримингом.

        cancel_event: asyncio.Event — установить для прерывания задачи.
        """
        process = None
        try:
            cmd = [
                self.claude_path,
                "-p",
                "--dangerously-skip-permissions",
                "--output-format", "stream-json",
                "--verbose",
                "--add-dir", self.working_directory,
            ]
            if memory_dir and os.path.isdir(memory_dir):
                cmd.extend(["--add-dir", memory_dir])
            if self.model:
                cmd.extend(["--model", self.model])
            if system_prompt_file and os.path.isfile(system_prompt_file):
                cmd.extend(["--append-system-prompt-file", os.path.abspath(system_prompt_file)])
            if session_id:
                cmd.extend(["--resume", session_id])
            cmd.append(prompt)

            logger.info("Запуск Claude CLI (streaming): '%s...'", prompt[:50])

            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory,
                # stream-json отдаёт весь результат инструмента одной строкой —
                # дефолтных 64 КиБ StreamReader не хватает (LimitOverrunError)
                limit=10 * 1024 * 1024,
            )

            full_response = []
            new_session_id = session_id
            cancelled = False

            while True:
                # Проверяем сигнал отмены
                if cancel_event and cancel_event.is_set():
                    process.terminate()
                    await asyncio.wait_for(process.wait(), timeout=5)
                    cancelled = True
                    break

                try:
                    line = await asyncio.wait_for(process.stdout.readline(), timeout=0.5)
                except asyncio.TimeoutError:
                    if process.returncode is not None:
                        break
                    continue

                if not line:
                    break

                try:
                    chunk = json.loads(line.decode("utf-8"))
                    if "session_id" in chunk:
                        new_session_id = chunk["session_id"]
                    text = self._extract_chunk_text(chunk)
                    if text:
                        full_response.append(text)
                        if on_chunk:
                            await on_chunk(text)
                except json.JSONDecodeError:
                    text = line.decode("utf-8").strip()
                    if text:
                        full_response.append(text)
                        if on_chunk:
                            await on_chunk(text)

            if not cancelled:
                await process.wait()

            self.current_session_id = new_session_id

            if cancelled:
                return {
                    "success": False,
                    "cancelled": True,
                    "error": "Задача остановлена пользователем",
                    "result": "".join(full_response),
                    "session_id": new_session_id,
                }

            if process.returncode != 0:
                stderr_text = ""
                try:
                    stderr_text = (await process.stderr.read()).decode("utf-8", errors="replace").strip()
                except Exception:
                    pass
                partial = "".join(full_response)
                error_detail = stderr_text or partial[:300] or f"exit code {process.returncode}"
                logger.error("Claude CLI streaming error (code %s): %s", process.returncode, error_detail[:500])
                return {
                    "success": False,
                    "cancelled": False,
                    "error": error_detail,
                    "result": partial,
                    "session_id": new_session_id,
                }

            return {
                "success": True,
                "cancelled": False,
                "result": "".join(full_response),
                "session_id": new_session_id,
            }

        except Exception as e:
            logger.error("Ошибка streaming: %s", e)
            if process:
                try:
                    process.terminate()
                except Exception:
                    pass
            return {
                "success": False,
                "cancelled": False,
                "error": str(e),
                "session_id": session_id,
            }

    # Иконки инструментов Claude для прогресс-индикатора
    TOOL_ICONS = {
        "Bash": "⚙️", "Read": "📖", "Write": "✏️", "Edit": "📝",
        "MultiEdit": "📝", "WebSearch": "🌐", "WebFetch": "🔗",
        "LS": "📂", "Glob": "🔍", "Grep": "🔎", "TodoWrite": "📋",
        "TodoRead": "📋", "Agent": "🤖", "Task": "🤖",
        "NotebookRead": "📒", "NotebookEdit": "📒",
    }

    def _extract_chunk_text(self, chunk: Dict[str, Any]) -> str:
        """Извлечь текст из stream-json события Claude CLI.

        Форматы событий (--output-format stream-json --verbose):
          type=assistant  → message.content[].type==text   — основной текст
          type=assistant  → message.content[].type==tool_use — вызов инструмента
          type=result     — итоговый текст (дубль, пропускаем)

        Для tool_use возвращаем строку с префиксом \\x00 (маркер инструмента)
        чтобы обработчик в tasks.py мог отделить инструменты от текста.
        """
        chunk_type = chunk.get("type", "")

        if chunk_type == "assistant":
            message = chunk.get("message", {})
            for block in message.get("content", []):
                if not isinstance(block, dict):
                    continue
                block_type = block.get("type", "")
                if block_type == "text":
                    return block.get("text", "")
                elif block_type == "tool_use":
                    tool_name = block.get("name", "?")
                    tool_input = block.get("input", {})
                    icon = self.TOOL_ICONS.get(tool_name, "🔧")
                    # Выбираем наиболее информативный параметр
                    if "command" in tool_input:
                        detail = str(tool_input["command"])[:80]
                    elif "file_path" in tool_input:
                        detail = os.path.basename(str(tool_input["file_path"]))
                    elif "path" in tool_input:
                        detail = os.path.basename(str(tool_input["path"]))
                    elif "query" in tool_input:
                        detail = str(tool_input["query"])[:60]
                    elif "url" in tool_input:
                        detail = str(tool_input["url"])[:60]
                    elif tool_input:
                        detail = str(next(iter(tool_input.values())))[:60]
                    else:
                        detail = ""
                    # \x00 — маркер инструмента для tasks.py
                    return f"\x00{icon} {tool_name}: {detail}"

        return ""

    async def check_availability(self) -> bool:
        """Проверить доступность Claude CLI"""
        try:
            process = await asyncio.create_subprocess_exec(
                self.claude_path, "--version",
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE
            )
            stdout, _ = await asyncio.wait_for(process.communicate(), timeout=10)
            
            if process.returncode == 0:
                version = stdout.decode().strip()
                logger.info(f"Claude CLI доступен: {version}")
                return True
            return False
            
        except Exception as e:
            logger.error(f"Claude CLI недоступен: {e}")
            return False

    def get_session_id(self) -> Optional[str]:
        """Получить текущий ID сессии"""
        return self.current_session_id

    def set_working_directory(self, path: str):
        """Установить рабочую директорию"""
        if os.path.isdir(path):
            self.working_directory = path
            logger.info(f"Рабочая директория: {path}")
        else:
            logger.warning(f"Директория не существует: {path}")
