import sqlite3
from datetime import datetime
from typing import Optional, List
from .models import Task, TaskStatus, User


class Database:
    def __init__(self, db_path: str = "claude_bot.db"):
        self.db_path = db_path
        self.init_db()

    def init_db(self):
        """Инициализация базы данных"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        # Таблица пользователей
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS users (
                user_id INTEGER PRIMARY KEY,
                username TEXT,
                created_at TEXT,
                last_activity TEXT,
                task_count INTEGER DEFAULT 0
            )
        """)

        # Выбор модели пользователя (чтобы голос/медиа видели выбор даже после перезапуска)
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS user_settings (
                user_id INTEGER PRIMARY KEY,
                model_key TEXT NOT NULL DEFAULT 'sonnet',
                updated_at TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        # Таблица задач
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS tasks (
                id TEXT PRIMARY KEY,
                user_id INTEGER NOT NULL,
                prompt TEXT NOT NULL,
                status TEXT NOT NULL,
                created_at TEXT NOT NULL,
                started_at TEXT,
                completed_at TEXT,
                result TEXT,
                error TEXT,
                FOREIGN KEY (user_id) REFERENCES users(user_id)
            )
        """)

        conn.commit()
        conn.close()

    def add_user(self, user_id: int, username: Optional[str] = None) -> User:
        """Добавить или обновить пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        cursor.execute("""
            INSERT OR REPLACE INTO users (user_id, username, created_at, last_activity)
            VALUES (?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?), ?)
        """, (user_id, username, user_id, now, now))

        conn.commit()
        user = self.get_user(user_id)
        conn.close()
        return user

    def get_user_model_key(self, user_id: int, default: str = "sonnet") -> str:
        """Получить выбранную модель пользователя из БД."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        cursor.execute(
            "SELECT model_key FROM user_settings WHERE user_id = ?",
            (user_id,),
        )
        row = cursor.fetchone()
        conn.close()
        return row[0] if row and row[0] else default

    def set_user_model_key(self, user_id: int, model_key: str) -> None:
        """Сохранить выбранную модель пользователя в БД."""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()
        cursor.execute(
            """
            INSERT OR REPLACE INTO user_settings (user_id, model_key, updated_at)
            VALUES (?, ?, ?)
            """,
            (user_id, model_key, now),
        )
        conn.commit()
        conn.close()

    def get_user(self, user_id: int) -> Optional[User]:
        """Получить пользователя по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT user_id, username, created_at, last_activity, task_count
            FROM users WHERE user_id = ?
        """, (user_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return User(
                user_id=row[0],
                username=row[1],
                created_at=datetime.fromisoformat(row[2]),
                last_activity=datetime.fromisoformat(row[3]),
                task_count=row[4]
            )
        return None

    def add_task(self, task: Task) -> Task:
        """Добавить новую задачу"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            INSERT INTO tasks (id, user_id, prompt, status, created_at, started_at, completed_at, result, error)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            task.id,
            task.user_id,
            task.prompt,
            task.status.value,
            task.created_at.isoformat(),
            task.started_at.isoformat() if task.started_at else None,
            task.completed_at.isoformat() if task.completed_at else None,
            task.result,
            task.error
        ))

        # Увеличить счётчик задач
        cursor.execute("UPDATE users SET task_count = task_count + 1 WHERE user_id = ?", (task.user_id,))

        conn.commit()
        conn.close()
        return task

    def update_task(self, task_id: str, status: TaskStatus, result: Optional[str] = None, error: Optional[str] = None):
        """Обновить статус задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()
        now = datetime.now().isoformat()

        updates = {"status": status.value, "completed_at": now}
        if result:
            updates["result"] = result
        if error:
            updates["error"] = error

        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id]

        cursor.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
        conn.commit()
        conn.close()

    def get_task(self, task_id: str) -> Optional[Task]:
        """Получить задачу по ID"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, prompt, status, created_at, started_at, completed_at, result, error
            FROM tasks WHERE id = ?
        """, (task_id,))

        row = cursor.fetchone()
        conn.close()

        if row:
            return Task(
                id=row[0],
                user_id=row[1],
                prompt=row[2],
                status=TaskStatus(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                started_at=datetime.fromisoformat(row[5]) if row[5] else None,
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                result=row[7],
                error=row[8]
            )
        return None

    def get_user_tasks(self, user_id: int, limit: int = 10) -> List[Task]:
        """Получить задачи пользователя"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, prompt, status, created_at, started_at, completed_at, result, error
            FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
        """, (user_id, limit))

        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append(Task(
                id=row[0],
                user_id=row[1],
                prompt=row[2],
                status=TaskStatus(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                started_at=datetime.fromisoformat(row[5]) if row[5] else None,
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                result=row[7],
                error=row[8]
            ))
        return tasks

    def get_pending_tasks(self) -> List[Task]:
        """Получить все незавершённые задачи"""
        conn = sqlite3.connect(self.db_path)
        cursor = conn.cursor()

        cursor.execute("""
            SELECT id, user_id, prompt, status, created_at, started_at, completed_at, result, error
            FROM tasks WHERE status IN (?, ?) ORDER BY created_at ASC
        """, (TaskStatus.PENDING.value, TaskStatus.RUNNING.value))

        rows = cursor.fetchall()
        conn.close()

        tasks = []
        for row in rows:
            tasks.append(Task(
                id=row[0],
                user_id=row[1],
                prompt=row[2],
                status=TaskStatus(row[3]),
                created_at=datetime.fromisoformat(row[4]),
                started_at=datetime.fromisoformat(row[5]) if row[5] else None,
                completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
                result=row[7],
                error=row[8]
            ))
        return tasks
