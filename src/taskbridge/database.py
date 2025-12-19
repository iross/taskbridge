"""Database operations for TaskBridge."""

import json
import sqlite3
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Any


@dataclass
class SyncLogEntry:
    """Sync log entry data structure."""

    id: int | None = None
    action: str = ""
    timestamp: datetime | None = None
    details: str = ""


@dataclass
class TodoistNoteMapping:
    """Todoist task to Obsidian note mapping."""

    id: int | None = None
    todoist_task_id: str = ""
    todoist_project_id: str | None = None
    note_path: str = ""
    obsidian_url: str = ""
    created_at: datetime | None = None
    updated_at: datetime | None = None


class Database:
    """Database operations for TaskBridge."""

    def __init__(self, db_path: str | None = None):
        if db_path is None:
            config_dir = Path.home() / ".taskbridge"
            config_dir.mkdir(exist_ok=True)
            db_path = str(config_dir / "mappings.db")

        self.db_path = db_path
        self._init_database()

    def _init_database(self) -> None:
        """Initialize database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            """
            )

            # Create indices for better performance
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp
                ON sync_log(timestamp)
            """
            )

            # Todoist notes mapping table
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS todoist_notes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    todoist_task_id TEXT UNIQUE NOT NULL,
                    todoist_project_id TEXT,
                    note_path TEXT NOT NULL,
                    obsidian_url TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_todoist_notes_task_id
                ON todoist_notes(todoist_task_id)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_todoist_notes_project_id
                ON todoist_notes(todoist_project_id)
            """
            )

            conn.commit()

    def log_sync_action(self, action: str, details: dict[str, Any] = None) -> int:
        """Log a sync action."""
        details_json = json.dumps(details) if details else None

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO sync_log (action, details)
                VALUES (?, ?)
            """,
                (action, details_json),
            )

            conn.commit()
            return cursor.lastrowid

    def get_sync_log(self, limit: int = 100) -> list[SyncLogEntry]:
        """Get recent sync log entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM sync_log
                ORDER BY timestamp DESC
                LIMIT ?
            """,
                (limit,),
            )

            entries = []
            for row in cursor.fetchall():
                entries.append(
                    SyncLogEntry(
                        id=row["id"],
                        action=row["action"],
                        timestamp=datetime.fromisoformat(row["timestamp"])
                        if row["timestamp"]
                        else None,
                        details=row["details"] or "",
                    )
                )
            return entries

    def clear_sync_log(self, older_than_days: int = 30) -> int:
        """Clear old sync log entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                f"""
                DELETE FROM sync_log
                WHERE timestamp < datetime('now', '-{older_than_days} days')
            """
            )

            conn.commit()
            return cursor.rowcount

    def create_todoist_note_mapping(self, mapping: TodoistNoteMapping) -> int:
        """Create a new Todoist task to Obsidian note mapping."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                INSERT INTO todoist_notes (
                    todoist_task_id, todoist_project_id, note_path, obsidian_url
                )
                VALUES (?, ?, ?, ?)
            """,
                (
                    mapping.todoist_task_id,
                    mapping.todoist_project_id,
                    mapping.note_path,
                    mapping.obsidian_url,
                ),
            )

            conn.commit()
            return cursor.lastrowid

    def get_todoist_note_by_task_id(self, task_id: str) -> TodoistNoteMapping | None:
        """Get Todoist note mapping by task ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM todoist_notes WHERE todoist_task_id = ?
            """,
                (task_id,),
            )

            row = cursor.fetchone()
            if row:
                return TodoistNoteMapping(
                    id=row["id"],
                    todoist_task_id=row["todoist_task_id"],
                    todoist_project_id=row["todoist_project_id"],
                    note_path=row["note_path"],
                    obsidian_url=row["obsidian_url"],
                    created_at=datetime.fromisoformat(row["created_at"])
                    if row["created_at"]
                    else None,
                    updated_at=datetime.fromisoformat(row["updated_at"])
                    if row["updated_at"]
                    else None,
                )
            return None

    def get_all_todoist_mappings(self) -> list[TodoistNoteMapping]:
        """Get all Todoist note mappings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute(
                """
                SELECT * FROM todoist_notes ORDER BY created_at DESC
            """
            )

            mappings = []
            for row in cursor.fetchall():
                mappings.append(
                    TodoistNoteMapping(
                        id=row["id"],
                        todoist_task_id=row["todoist_task_id"],
                        todoist_project_id=row["todoist_project_id"],
                        note_path=row["note_path"],
                        obsidian_url=row["obsidian_url"],
                        created_at=datetime.fromisoformat(row["created_at"])
                        if row["created_at"]
                        else None,
                        updated_at=datetime.fromisoformat(row["updated_at"])
                        if row["updated_at"]
                        else None,
                    )
                )
            return mappings

    def update_todoist_note_mapping(self, mapping: TodoistNoteMapping) -> bool:
        """Update an existing Todoist note mapping."""
        if not mapping.id:
            return False

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute(
                """
                UPDATE todoist_notes
                SET todoist_project_id = ?, note_path = ?, obsidian_url = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """,
                (mapping.todoist_project_id, mapping.note_path, mapping.obsidian_url, mapping.id),
            )

            conn.commit()
            return cursor.rowcount > 0


# Global database instance
db = Database()
