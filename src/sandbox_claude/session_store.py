"""
SQLite session storage for sandbox-claude containers.
"""

import json
import sqlite3
from pathlib import Path
from typing import Any, Optional


class SessionStore:
    """Manages persistent storage of container sessions."""

    def __init__(self, db_path: Optional[Path] = None):
        """Initialize the session store."""
        if db_path is None:
            # Default to ~/.sandbox_claude/sessions.db
            self.db_path = Path.home() / ".sandbox_claude" / "sessions.db"
        else:
            self.db_path = Path(db_path)

        # Ensure directory exists
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        # Initialize database
        self._init_database()

    def _init_database(self) -> None:
        """Initialize the SQLite database schema."""
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS sandboxes (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    container_id TEXT UNIQUE NOT NULL,
                    project_name TEXT NOT NULL,
                    feature_name TEXT NOT NULL,
                    container_name TEXT UNIQUE NOT NULL,
                    status TEXT DEFAULT 'created',
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    last_accessed TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    working_dir TEXT,
                    docker_image TEXT,
                    metadata TEXT
                )
            """
            )

            # Create indexes for efficient queries
            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_project
                ON sandboxes(project_name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_feature
                ON sandboxes(feature_name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_project_feature
                ON sandboxes(project_name, feature_name)
            """
            )

            conn.execute(
                """
                CREATE INDEX IF NOT EXISTS idx_status
                ON sandboxes(status)
            """
            )

            conn.commit()

    def add_container(
        self,
        container_id: str,
        container_name: str,
        project_name: str,
        feature_name: str,
        working_dir: Optional[str] = None,
        docker_image: Optional[str] = None,
        metadata: Optional[dict[str, Any]] = None,
    ) -> bool:
        """Add a new container to the store."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    INSERT INTO sandboxes (
                        container_id, container_name, project_name,
                        feature_name, working_dir, docker_image,
                        metadata, status
                    ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                    (
                        container_id,
                        container_name,
                        project_name,
                        feature_name,
                        working_dir,
                        docker_image,
                        json.dumps(metadata) if metadata else None,
                        "running",
                    ),
                )
                conn.commit()
                return True
        except sqlite3.IntegrityError:
            # Container already exists
            return False

    def get_container(self, container_id: str) -> Optional[dict[str, Any]]:
        """Get container information by ID."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(
                """
                SELECT * FROM sandboxes WHERE container_id = ?
            """,
                (container_id,),
            )

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def find_container(
        self,
        project: Optional[str] = None,
        feature: Optional[str] = None,
        status: Optional[str] = None,
    ) -> Optional[dict[str, Any]]:
        """Find container by project and/or feature."""
        query = "SELECT * FROM sandboxes WHERE 1=1"
        params = []

        if project:
            query += " AND project_name = ?"
            params.append(project)

        if feature:
            query += " AND feature_name = ?"
            params.append(feature)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC LIMIT 1"

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)

            row = cursor.fetchone()
            if row:
                return dict(row)
            return None

    def list_containers(
        self,
        project: Optional[str] = None,
        feature: Optional[str] = None,
        status: Optional[str] = None,
        limit: Optional[int] = None,
    ) -> list[dict[str, Any]]:
        """List containers with optional filters."""
        query = "SELECT * FROM sandboxes WHERE 1=1"
        params = []

        if project:
            query += " AND project_name = ?"
            params.append(project)

        if feature:
            query += " AND feature_name = ?"
            params.append(feature)

        if status:
            query += " AND status = ?"
            params.append(status)

        query += " ORDER BY created_at DESC"

        if limit:
            query += " LIMIT ?"
            params.append(str(limit))

        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            cursor = conn.cursor()
            cursor.execute(query, params)

            return [dict(row) for row in cursor.fetchall()]

    def update_container_status(self, container_id: str, status: str) -> bool:
        """Update the status of a container."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE sandboxes
                    SET status = ?, last_accessed = CURRENT_TIMESTAMP
                    WHERE container_id = ?
                """,
                    (status, container_id),
                )
                conn.commit()
                return conn.total_changes > 0
        except sqlite3.Error:
            return False

    def update_last_accessed(self, container_id: str) -> bool:
        """Update the last accessed timestamp."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    UPDATE sandboxes
                    SET last_accessed = CURRENT_TIMESTAMP
                    WHERE container_id = ?
                """,
                    (container_id,),
                )
                conn.commit()
                return conn.total_changes > 0
        except sqlite3.Error:
            return False

    def remove_container(self, container_id: str) -> bool:
        """Remove a container from the store."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                conn.execute(
                    """
                    DELETE FROM sandboxes WHERE container_id = ?
                """,
                    (container_id,),
                )
                conn.commit()
                return conn.total_changes > 0
        except sqlite3.Error:
            return False

    def get_statistics(self) -> dict[str, Any]:
        """Get statistics about stored containers."""
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            # Total containers
            cursor.execute("SELECT COUNT(*) FROM sandboxes")
            total = cursor.fetchone()[0]

            # Running containers
            cursor.execute("SELECT COUNT(*) FROM sandboxes WHERE status = 'running'")
            running = cursor.fetchone()[0]

            # Containers by project
            cursor.execute(
                """
                SELECT project_name, COUNT(*) as count
                FROM sandboxes
                GROUP BY project_name
                ORDER BY count DESC
            """
            )
            by_project = cursor.fetchall()

            # Recently accessed
            cursor.execute(
                """
                SELECT container_name, last_accessed
                FROM sandboxes
                ORDER BY last_accessed DESC
                LIMIT 5
            """
            )
            recent = cursor.fetchall()

            return {
                "total": total,
                "running": running,
                "by_project": by_project,
                "recent": recent,
            }

    def cleanup_old_records(self, days: int = 30) -> int:
        """Remove records older than specified days."""
        try:
            with sqlite3.connect(self.db_path) as conn:
                cursor = conn.cursor()
                cursor.execute(
                    """
                    DELETE FROM sandboxes
                    WHERE status != 'running'
                    AND datetime(last_accessed) < datetime('now', ? || ' days')
                """,
                    (-days,),
                )
                conn.commit()
                return cursor.rowcount
        except sqlite3.Error:
            return 0

    def export_sessions(self, output_path: Path) -> bool:
        """Export all sessions to a JSON file."""
        try:
            sessions = self.list_containers()
            with open(output_path, "w") as f:
                json.dump(sessions, f, indent=2, default=str)
            return True
        except Exception:
            return False

    def import_sessions(self, input_path: Path) -> int:
        """Import sessions from a JSON file."""
        try:
            with open(input_path) as f:
                sessions = json.load(f)

            imported = 0
            for session in sessions:
                if self.add_container(
                    container_id=session["container_id"],
                    container_name=session["container_name"],
                    project_name=session["project_name"],
                    feature_name=session["feature_name"],
                    working_dir=session.get("working_dir"),
                    docker_image=session.get("docker_image"),
                    metadata=json.loads(session.get("metadata", "{}")),
                ):
                    imported += 1

            return imported
        except Exception:
            return 0
