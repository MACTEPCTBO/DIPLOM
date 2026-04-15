import sqlite3
import json
from pathlib import Path
from typing import Optional, Dict, Any

DB_PATH = Path("player_data.db")

class TokenStorage:
    def __init__(self):
        self._init_db()

    def _get_connection(self):
        conn = sqlite3.connect(str(DB_PATH))
        conn.row_factory = sqlite3.Row
        return conn

    def _init_db(self):
        with self._get_connection() as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_tokens(self, access_token: str, refresh_token: str):
        with self._get_connection() as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tokens (id, access_token, refresh_token, updated_at)
                VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            """, (access_token, refresh_token))
        print(access_token)

    def load_tokens(self) -> Optional[Dict[str, str]]:
        with self._get_connection() as conn:
            row = conn.execute("SELECT access_token, refresh_token FROM tokens WHERE id = 1").fetchone()



            if row:
                return {"access_token": row["access_token"], "refresh_token": row["refresh_token"]}
        return None

    def clear_tokens(self):
        with self._get_connection() as conn:
            conn.execute("DELETE FROM tokens WHERE id = 1")