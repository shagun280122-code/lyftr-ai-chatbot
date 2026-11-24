
import os
import sqlite3
from pathlib import Path
from datetime import datetime, timezone

DATABASE_URL = os.getenv("DATABASE_URL", "sqlite:///./app.db")

def get_db_path():
    prefix = "sqlite:///"
    if DATABASE_URL.startswith(prefix):
        path = DATABASE_URL[len(prefix):]
    else:
        path = "./app.db"

    db_path = Path(path)
    if not db_path.is_absolute():
        db_path = Path.cwd() / db_path

    db_path.parent.mkdir(parents=True, exist_ok=True)
    return str(db_path)

def get_connection():
    connection = sqlite3.connect(get_db_path(), timeout=30)
    connection.row_factory = sqlite3.Row
    return connection

def init_db():
    with get_connection() as conn:
        conn.execute("""
            CREATE TABLE IF NOT EXISTS sessions (
                session_id TEXT PRIMARY KEY,
                system_prompt TEXT,
                created_at TEXT NOT NULL
            )
        """)

        conn.execute("""
            CREATE TABLE IF NOT EXISTS messages (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_id TEXT NOT NULL,
                role TEXT NOT NULL,
                content TEXT NOT NULL,
                metadata TEXT,
                created_at TEXT NOT NULL,
                FOREIGN KEY(session_id) REFERENCES sessions(session_id)
            )
        """)

        conn.execute("""
            CREATE INDEX IF NOT EXISTS idx_messages_session
            ON messages(session_id, id)
        """)

def utc_now():
    return datetime.now(timezone.utc).isoformat()

def create_session(session_id, system_prompt=None):
    with get_connection() as conn:
        conn.execute(
            "INSERT INTO sessions VALUES (?, ?, ?)",
            (session_id, system_prompt, utc_now())
        )

def get_session(session_id):
    with get_connection() as conn:
        return conn.execute(
            "SELECT * FROM sessions WHERE session_id = ?",
            (session_id,)
        ).fetchone()

def update_system_prompt(session_id, prompt):
    with get_connection() as conn:
        conn.execute(
            "UPDATE sessions SET system_prompt = ? WHERE session_id = ?",
            (prompt, session_id)
        )

def get_messages(session_id):
    with get_connection() as conn:
        return conn.execute(
            """SELECT role, content, metadata
               FROM messages WHERE session_id = ?
               ORDER BY id ASC""",
            (session_id,)
        ).fetchall()

def save_message(session_id, role, content, metadata=None):
    import json

    with get_connection() as conn:
        conn.execute(
            """INSERT INTO messages
               (session_id, role, content, metadata, created_at)
               VALUES (?, ?, ?, ?, ?)""",
            (
                session_id,
                role,
                content,
                json.dumps(metadata) if metadata is not None else None,
                utc_now()
            )
        )
