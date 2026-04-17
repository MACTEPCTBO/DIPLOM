import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any
from models import Track, Playlist

class SearchHistoryStorage:
    def __init__(self, db_path: Path = Path("search_history.db")):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT NOT NULL,
                    timestamp REAL NOT NULL,
                    tracks_json TEXT NOT NULL
                )
            """)

    def add_entry(self, query: str, playlist: Playlist):
        """Сохраняет плейлист (результат поиска) в историю."""
        tracks_json = json.dumps([t.to_dict() for t in playlist.tracks])
        timestamp = datetime.now().timestamp()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (query, timestamp, tracks_json) VALUES (?, ?, ?)",
                (query, timestamp, tracks_json)
            )

    def get_entries(self) -> List[Dict[str, Any]]:
        """Возвращает список записей истории (без треков для оптимизации)."""
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT id, query, timestamp FROM history ORDER BY timestamp DESC"
            ).fetchall()
        return [{"id": row["id"], "query": row["query"], "timestamp": row["timestamp"]} for row in rows]

    def get_playlist_by_id(self, entry_id: int) -> Optional[Playlist]:
        """Восстанавливает плейлист по ID записи."""
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT query, tracks_json FROM history WHERE id = ?", (entry_id,)
            ).fetchone()
        if not row:
            return None
        tracks_data = json.loads(row[1])
        tracks = [Track.from_dict(t) for t in tracks_data]
        return Playlist(
            name=f"История: {row[0]}",
            tracks=tracks,
            playlist_type="server",
            id=entry_id
        )