import sqlite3
import json
from pathlib import Path
from datetime import datetime
from typing import List, Optional
from models import Track, HistoryEntry


class HistoryStorage:
    def __init__(self, db_path: Path = Path("history.db")):
        self.db_path = db_path
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS history (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    track_json TEXT NOT NULL,
                    timestamp REAL NOT NULL
                )
            """)
            conn.execute("CREATE INDEX IF NOT EXISTS idx_timestamp ON history(timestamp)")

    def save_entry(self, entry: HistoryEntry):
        track_dict = entry.track.to_dict()
        track_json = json.dumps(track_dict, ensure_ascii=False)
        timestamp = entry.timestamp.timestamp()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                "INSERT INTO history (track_json, timestamp) VALUES (?, ?)",
                (track_json, timestamp)
            )

    def load_entries(self, limit: int = 200) -> List[HistoryEntry]:
        with sqlite3.connect(self.db_path) as conn:
            conn.row_factory = sqlite3.Row
            rows = conn.execute(
                "SELECT track_json, timestamp FROM history ORDER BY timestamp DESC LIMIT ?",
                (limit,)
            ).fetchall()
        entries = []
        for row in rows:
            track_data = json.loads(row["track_json"])
            track = Track.from_dict(track_data)
            timestamp = datetime.fromtimestamp(row["timestamp"])
            entries.append(HistoryEntry(track=track, timestamp=timestamp))
        return list(reversed(entries))

    def clear_history(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM history")