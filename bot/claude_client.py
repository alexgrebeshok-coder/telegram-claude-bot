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
        timeout: int = 300
    ) -> Dict[str, Any]:
        """
        Выполнить задачу через Claude Code CLI
        
        Args:
            prompt: Текст задачи
            session_id: ID сессии для продолжения (опционально)
            timeout: Таймаут в секундах (по умолчанию 5 минут)
            
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
                "--add-dir", self.working_directory,  # Доступ только к рабочей директории
            ]
            
            # Модель
            if self.model:
                cmd.extend(["--model", self.model])
            
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
                logger.error(f"Claude CLI ошибка (код {process.returncode}): {stderr_text}")
                return {
                    "success": False,
                    "error": f"Claude Code ошибка: {stderr_text or 'Неизвестная ошибка'}",
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
        on_chunk: Optional[Callable] = None
    ) -> Dict[str, Any]:
        """
        Выполнить задачу со стримингом (для длинных задач)
        
        Args:
            prompt: Текст задачи
            session_id: ID сессии
            on_chunk: Callback для каждого чанка текста
            
        Returns:
            Финальный результат
        """
        try:
            cmd = [
                self.claude_path,
                "-p",
                "--dangerously-skip-permissions",
                "--output-format", "stream-json",
            ]
            
            if session_id:
                cmd.extend(["--resume", session_id])
            
            cmd.append(prompt)
            
            logger.info(f"Запуск Claude CLI (streaming): '{prompt[:50]}...'")
            
            process = await asyncio.create_subprocess_exec(
                *cmd,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=self.working_directory
            )
            
            full_response = []
            new_session_id = session_id
            
            # Читаем stdout построчно
            while True:
                line = await process.stdout.readline()
                if not line:
                    break
                
                try:
                    chunk = json.loads(line.decode("utf-8"))
                    
                    # Извлекаем session_id
                    if "session_id" in chunk:
                        new_session_id = chunk["session_id"]
                    
                    # Извлекаем текст
                    text = self._extract_chunk_text(chunk)
                    if text:
                        full_response.append(text)
                        if on_chunk:
                            await on_chunk(text)
                            
                except json.JSONDecodeError:
                    # Не JSON строка — добавляем как есть
                    text = line.decode("utf-8").strip()
                    if text:
                        full_response.append(text)
                        if on_chunk:
                            await on_chunk(text)
            
            await process.wait()
            
            self.current_session_id = new_session_id
            
            return {
                "success": process.returncode == 0,
                "result": "".join(full_response),
                "session_id": new_session_id
            }
            
        except Exception as e:
            logger.error(f"Ошибка streaming: {e}")
            return {
                "success": False,
                "error": str(e),
                "session_id": session_id
            }

    def _extract_chunk_text(self, chunk: Dict[str, Any]) -> str:
        """Извлечь текст из streaming чанка"""
        if "content" in chunk:
            content = chunk["content"]
            if isinstance(content, str):
                return content
            if isinstance(content, list):
                for block in content:
                    if isinstance(block, dict) and block.get("type") == "text":
                        return block.get("text", "")
        
        if "delta" in chunk:
            delta = chunk["delta"]
            if isinstance(delta, dict):
                return delta.get("text", "")
            return str(delta)
        
        if "text" in chunk:
            return chunk["text"]
        
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
