"""Database operations for TaskBridge."""

import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Dict, Any, Optional
from dataclasses import dataclass


@dataclass
class Project:
    """Project mapping data structure."""
    id: Optional[int] = None
    linear_id: Optional[str] = None
    linear_name: Optional[str] = None
    toggl_client_id: Optional[str] = None
    toggl_project_id: Optional[str] = None
    created_at: Optional[datetime] = None
    updated_at: Optional[datetime] = None


@dataclass
class SyncLogEntry:
    """Sync log entry data structure."""
    id: Optional[int] = None
    action: str = ""
    timestamp: Optional[datetime] = None
    details: str = ""


class Database:
    """Database operations for TaskBridge."""
    
    def __init__(self, db_path: Optional[str] = None):
        if db_path is None:
            config_dir = Path.home() / ".taskbridge"
            config_dir.mkdir(exist_ok=True)
            db_path = str(config_dir / "mappings.db")
        
        self.db_path = db_path
        self._init_database()
    
    def _init_database(self) -> None:
        """Initialize database with required tables."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    linear_id TEXT,
                    linear_name TEXT,
                    toggl_client_id TEXT,
                    toggl_project_id TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)
            
            conn.execute("""
                CREATE TABLE IF NOT EXISTS sync_log (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    details TEXT
                )
            """)
            
            # Create indices for better performance
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_linear_id 
                ON projects(linear_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_projects_toggl_ids 
                ON projects(toggl_client_id, toggl_project_id)
            """)
            
            conn.execute("""
                CREATE INDEX IF NOT EXISTS idx_sync_log_timestamp 
                ON sync_log(timestamp)
            """)
            
            conn.commit()
    
    def create_project(self, project: Project) -> int:
        """Create a new project mapping."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO projects (linear_id, linear_name, toggl_client_id, toggl_project_id)
                VALUES (?, ?, ?, ?)
            """, (project.linear_id, project.linear_name, project.toggl_client_id, project.toggl_project_id))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_project(self, project_id: int) -> Optional[Project]:
        """Get a project by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM projects WHERE id = ?
            """, (project_id,))
            
            row = cursor.fetchone()
            if row:
                return Project(
                    id=row['id'],
                    linear_id=row['linear_id'],
                    linear_name=row['linear_name'],
                    toggl_client_id=row['toggl_client_id'],
                    toggl_project_id=row['toggl_project_id'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                )
            return None
    
    def get_project_by_linear_id(self, linear_id: str) -> Optional[Project]:
        """Get a project by Linear ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM projects WHERE linear_id = ?
            """, (linear_id,))
            
            row = cursor.fetchone()
            if row:
                return Project(
                    id=row['id'],
                    linear_id=row['linear_id'],
                    linear_name=row['linear_name'],
                    toggl_client_id=row['toggl_client_id'],
                    toggl_project_id=row['toggl_project_id'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                )
            return None
    
    def get_project_by_toggl_ids(self, toggl_client_id: str, toggl_project_id: str) -> Optional[Project]:
        """Get a project by Toggl client and project IDs."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM projects WHERE toggl_client_id = ? AND toggl_project_id = ?
            """, (toggl_client_id, toggl_project_id))
            
            row = cursor.fetchone()
            if row:
                return Project(
                    id=row['id'],
                    linear_id=row['linear_id'],
                    linear_name=row['linear_name'],
                    toggl_client_id=row['toggl_client_id'],
                    toggl_project_id=row['toggl_project_id'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                )
            return None
    
    def get_all_projects(self) -> List[Project]:
        """Get all project mappings."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM projects ORDER BY created_at DESC
            """)
            
            projects = []
            for row in cursor.fetchall():
                projects.append(Project(
                    id=row['id'],
                    linear_id=row['linear_id'],
                    linear_name=row['linear_name'],
                    toggl_client_id=row['toggl_client_id'],
                    toggl_project_id=row['toggl_project_id'],
                    created_at=datetime.fromisoformat(row['created_at']) if row['created_at'] else None,
                    updated_at=datetime.fromisoformat(row['updated_at']) if row['updated_at'] else None
                ))
            return projects
    
    def update_project(self, project: Project) -> bool:
        """Update an existing project mapping."""
        if not project.id:
            return False
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                UPDATE projects 
                SET linear_id = ?, linear_name = ?, toggl_client_id = ?, toggl_project_id = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
            """, (project.linear_id, project.linear_name, project.toggl_client_id, 
                  project.toggl_project_id, project.id))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def delete_project(self, project_id: int) -> bool:
        """Delete a project mapping."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM projects WHERE id = ?
            """, (project_id,))
            
            conn.commit()
            return cursor.rowcount > 0
    
    def log_sync_action(self, action: str, details: Dict[str, Any] = None) -> int:
        """Log a sync action."""
        details_json = json.dumps(details) if details else None
        
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                INSERT INTO sync_log (action, details)
                VALUES (?, ?)
            """, (action, details_json))
            
            conn.commit()
            return cursor.lastrowid
    
    def get_sync_log(self, limit: int = 100) -> List[SyncLogEntry]:
        """Get recent sync log entries."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.execute("""
                SELECT * FROM sync_log 
                ORDER BY timestamp DESC 
                LIMIT ?
            """, (limit,))
            
            entries = []
            for row in cursor.fetchall():
                entries.append(SyncLogEntry(
                    id=row['id'],
                    action=row['action'],
                    timestamp=datetime.fromisoformat(row['timestamp']) if row['timestamp'] else None,
                    details=row['details'] or ""
                ))
            return entries
    
    def clear_sync_log(self, older_than_days: int = 30) -> int:
        """Clear old sync log entries."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("""
                DELETE FROM sync_log 
                WHERE timestamp < datetime('now', '-{} days')
            """.format(older_than_days))
            
            conn.commit()
            return cursor.rowcount


# Global database instance
db = Database()