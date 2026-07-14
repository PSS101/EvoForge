import sqlite3
import os
from datetime import datetime

DEFAULT_DB_PATH = os.path.join(os.path.dirname(__file__), "project_state.db")

class DBManager:
    def __init__(self, db_path=DEFAULT_DB_PATH):
        self.db_path = db_path
        os.makedirs(os.path.dirname(self.db_path), exist_ok=True)
        self.init_db()

    def get_connection(self):
        return sqlite3.connect(self.db_path)

    def init_db(self):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            # Projects table
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS projects (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL UNIQUE,
                    path TEXT NOT NULL,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                );
            """)
            # File Registry
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS file_registry (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    file_path TEXT NOT NULL,
                    file_type TEXT NOT NULL, -- 'source', 'test', 'doc', 'spec'
                    content_hash TEXT NOT NULL,
                    last_modified TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id),
                    UNIQUE(project_id, file_path)
                );
            """)
            # SDLC Runs
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS sdlc_runs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    run_date TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    srs_hash TEXT,
                    design_hash TEXT,
                    status TEXT, -- 'success', 'failed'
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            # SRS version history for incremental comparison
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS srs_versions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    version INTEGER,
                    content_hash TEXT,
                    content TEXT,
                    note TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            # Dependency graph storage and extracted metadata
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS dependency_graphs (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    project_id INTEGER,
                    graph_type TEXT,
                    file_path TEXT,
                    graph_json TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY(project_id) REFERENCES projects(id)
                );
            """)
            conn.commit()

    def register_project(self, name, path):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            try:
                cursor.execute(
                    "INSERT INTO projects (name, path) VALUES (?, ?)", (name, path)
                )
                conn.commit()
                return cursor.lastrowid
            except sqlite3.IntegrityError:
                cursor.execute("SELECT id FROM projects WHERE name = ?", (name,))
                return cursor.fetchone()[0]

    def get_project(self, name):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT id, name, path FROM projects WHERE name = ?", (name,))
            return cursor.fetchone()

    def register_file(self, project_id, file_path, file_type, content_hash):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            now = datetime.now().isoformat()
            cursor.execute("""
                INSERT INTO file_registry (project_id, file_path, file_type, content_hash, last_modified)
                VALUES (?, ?, ?, ?, ?)
                ON CONFLICT(project_id, file_path) DO UPDATE SET
                    content_hash = excluded.content_hash,
                    last_modified = excluded.last_modified
            """, (project_id, file_path, file_type, content_hash, now))
            conn.commit()

    def get_file_registry(self, project_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_path, file_type, content_hash, last_modified FROM file_registry WHERE project_id = ?",
                (project_id,)
            )
            return cursor.fetchall()

    def get_registered_file(self, project_id, file_path):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT file_path, file_type, content_hash, last_modified FROM file_registry WHERE project_id = ? AND file_path = ?",
                (project_id, file_path)
            )
            return cursor.fetchone()

    def log_run(self, project_id, srs_hash, design_hash, status):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO sdlc_runs (project_id, srs_hash, design_hash, status)
                VALUES (?, ?, ?, ?)
            """, (project_id, srs_hash, design_hash, status))
            conn.commit()
            return cursor.lastrowid

    def get_last_run(self, project_id):
        with self.get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT srs_hash, design_hash, status FROM sdlc_runs
                WHERE project_id = ? ORDER BY run_date DESC LIMIT 1
            """, (project_id,))
            return cursor.fetchone()
