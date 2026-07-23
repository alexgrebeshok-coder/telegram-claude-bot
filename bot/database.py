import aiosqlite
from datetime import datetime
from typing import Optional, List
from .models import Task, TaskStatus, User


class Database:
    def __init__(self, db_path: str = "claude_bot.db"):
        self.db_path = db_path

    async def init_db(self):
        """Инициализация и idempotent-миграции."""
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                CREATE TABLE IF NOT EXISTS users (
                    user_id INTEGER PRIMARY KEY,
                    username TEXT,
                    created_at TEXT,
                    last_activity TEXT,
                    task_count INTEGER DEFAULT 0
                )
            """)
            await db.execute("""
                CREATE TABLE IF NOT EXISTS user_settings (
                    user_id INTEGER PRIMARY KEY,
                    model_key TEXT NOT NULL DEFAULT 'sonnet',
                    updated_at TEXT,
                    FOREIGN KEY (user_id) REFERENCES users(user_id)
                )
            """)
            await db.execute("""
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
            # Migrations — add new columns if missing
            for col, typ in [("session_id", "TEXT"), ("working_dir", "TEXT")]:
                try:
                    await db.execute(f"ALTER TABLE user_settings ADD COLUMN {col} {typ}")
                except Exception:
                    pass
            await db.commit()

    async def add_user(self, user_id: int, username: Optional[str] = None) -> Optional[User]:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT OR REPLACE INTO users (user_id, username, created_at, last_activity)
                VALUES (?, ?, COALESCE((SELECT created_at FROM users WHERE user_id = ?), ?), ?)
            """, (user_id, username, user_id, now, now))
            await db.commit()
        return await self.get_user(user_id)

    async def get_user_model_key(self, user_id: int, default: str = "sonnet") -> str:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT model_key FROM user_settings WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else default

    async def set_user_model_key(self, user_id: int, model_key: str) -> None:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_settings (user_id, model_key, updated_at)
                VALUES (?, ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET model_key = excluded.model_key, updated_at = excluded.updated_at
            """, (user_id, model_key, now))
            await db.commit()

    async def get_user_session(self, user_id: int) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT session_id FROM user_settings WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def set_user_session(self, user_id: int, session_id: Optional[str]) -> None:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_settings (user_id, model_key, session_id, updated_at)
                VALUES (?, 'sonnet', ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET session_id = excluded.session_id, updated_at = excluded.updated_at
            """, (user_id, session_id, now))
            await db.commit()

    async def get_user_working_dir(self, user_id: int) -> Optional[str]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT working_dir FROM user_settings WHERE user_id = ?", (user_id,)
            )
            row = await cursor.fetchone()
            return row[0] if row and row[0] else None

    async def set_user_working_dir(self, user_id: int, working_dir: str) -> None:
        now = datetime.now().isoformat()
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
                INSERT INTO user_settings (user_id, model_key, working_dir, updated_at)
                VALUES (?, 'sonnet', ?, ?)
                ON CONFLICT(user_id) DO UPDATE SET working_dir = excluded.working_dir, updated_at = excluded.updated_at
            """, (user_id, working_dir, now))
            await db.commit()

    async def get_all_sessions(self) -> dict:
        """Все (user_id → session_id) для восстановления при старте."""
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute(
                "SELECT user_id, session_id FROM user_settings WHERE session_id IS NOT NULL AND session_id != ''"
            )
            rows = await cursor.fetchall()
            return {row[0]: row[1] for row in rows}

    async def get_user(self, user_id: int) -> Optional[User]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT user_id, username, created_at, last_activity, task_count
                FROM users WHERE user_id = ?
            """, (user_id,))
            row = await cursor.fetchone()
        if row:
            return User(
                user_id=row[0],
                username=row[1],
                created_at=datetime.fromisoformat(row[2]),
                last_activity=datetime.fromisoformat(row[3]),
                task_count=row[4],
            )
        return None

    async def add_task(self, task: Task) -> Task:
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute("""
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
                task.error,
            ))
            await db.execute(
                "UPDATE users SET task_count = task_count + 1 WHERE user_id = ?", (task.user_id,)
            )
            await db.commit()
        return task

    async def update_task(
        self,
        task_id: str,
        status: TaskStatus,
        result: Optional[str] = None,
        error: Optional[str] = None,
    ):
        now = datetime.now().isoformat()
        updates = {"status": status.value, "completed_at": now}
        if result:
            updates["result"] = result
        if error:
            updates["error"] = error
        set_clause = ", ".join([f"{k} = ?" for k in updates.keys()])
        values = list(updates.values()) + [task_id]
        async with aiosqlite.connect(self.db_path) as db:
            await db.execute(f"UPDATE tasks SET {set_clause} WHERE id = ?", values)
            await db.commit()

    async def get_task(self, task_id: str) -> Optional[Task]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, user_id, prompt, status, created_at, started_at, completed_at, result, error
                FROM tasks WHERE id = ?
            """, (task_id,))
            row = await cursor.fetchone()
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
                error=row[8],
            )
        return None

    async def get_user_tasks(self, user_id: int, limit: int = 10) -> List[Task]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, user_id, prompt, status, created_at, started_at, completed_at, result, error
                FROM tasks WHERE user_id = ? ORDER BY created_at DESC LIMIT ?
            """, (user_id, limit))
            rows = await cursor.fetchall()
        return [self._row_to_task(r) for r in rows]

    async def get_pending_tasks(self) -> List[Task]:
        async with aiosqlite.connect(self.db_path) as db:
            cursor = await db.execute("""
                SELECT id, user_id, prompt, status, created_at, started_at, completed_at, result, error
                FROM tasks WHERE status IN (?, ?) ORDER BY created_at ASC
            """, (TaskStatus.PENDING.value, TaskStatus.RUNNING.value))
            rows = await cursor.fetchall()
        return [self._row_to_task(r) for r in rows]

    @staticmethod
    def _row_to_task(row) -> Task:
        return Task(
            id=row[0],
            user_id=row[1],
            prompt=row[2],
            status=TaskStatus(row[3]),
            created_at=datetime.fromisoformat(row[4]),
            started_at=datetime.fromisoformat(row[5]) if row[5] else None,
            completed_at=datetime.fromisoformat(row[6]) if row[6] else None,
            result=row[7],
            error=row[8],
        )
