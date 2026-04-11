import json
import os
from datetime import datetime

class HistoryManager:
    def __init__(self, filename="history.json"):
        self.filename = filename
        self.ratings_filename = "ratings.json"
        self._history = []
        self._ratings = {}  # source -> rating ("like"/"dislike")
        self._load()
        self._load_ratings()

    def _load(self):
        if os.path.exists(self.filename):
            try:
                with open(self.filename, 'r', encoding='utf-8') as f:
                    self._history = json.load(f)
            except:
                self._history = []

    def _save(self):
        with open(self.filename, 'w', encoding='utf-8') as f:
            json.dump(self._history, f, indent=2, ensure_ascii=False)

    def _load_ratings(self):
        if os.path.exists(self.ratings_filename):
            try:
                with open(self.ratings_filename, 'r', encoding='utf-8') as f:
                    self._ratings = json.load(f)
            except:
                self._ratings = {}

    def _save_ratings(self):
        with open(self.ratings_filename, 'w', encoding='utf-8') as f:
            json.dump(self._ratings, f, indent=2, ensure_ascii=False)

    def add_entry(self, title, source):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        entry = [title, source, timestamp]
        self._history.append(entry)
        self._save()

    def get_history(self):
        return self._history

    def add_rating(self, source, rating):
        self._ratings[source] = rating
        self._save_ratings()

    def get_rating(self, source):
        return self._ratings.get(source, None)