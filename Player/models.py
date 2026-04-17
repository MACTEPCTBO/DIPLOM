from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any
from datetime import datetime


@dataclass
class Track:
    """Модель трека"""
    id: Optional[int] = None
    title: str = ""
    artist: str = ""
    duration_ms: int = 0
    url: str = ""
    is_local: bool = False
    server_id: Optional[int] = None
    album: str = ""
    cover_uri: str = ""

    def display_text(self) -> str:
        artist_str = self.artist or "Unknown Artist"
        return f"{artist_str} - {self.title}"

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "title": self.title,
            "artist": self.artist,
            "duration_ms": self.duration_ms,
            "url": self.url,
            "is_local": self.is_local,
            "server_id": self.server_id,
            "album": self.album,
            "cover_uri": self.cover_uri
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Track':
        return cls(**data)


@dataclass
class Playlist:
    name: str
    tracks: List[Track] = field(default_factory=list)
    playlist_type: str = "local"
    count: int = 0
    id: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return {
            "id": self.id,
            "name": self.name,
            "type": self.playlist_type,
            "count": len(self.tracks),
            "tracks": [t.to_dict() for t in self.tracks]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playlist':
        tracks = [Track.from_dict(t) for t in data.get("tracks", [])]
        return cls(
            id=data.get("id", 0),
            name=data["name"],
            tracks=tracks,
            playlist_type=data.get("type", "local"),
            count=data.get("count", len(tracks))
        )


@dataclass
class HistoryEntry:
    """Запись в истории прослушивания"""
    track: Track
    timestamp: datetime = field(default_factory=datetime.now)

    def display_text(self) -> str:
        time_str = self.timestamp.strftime("%H:%M")
        return f"{time_str}  {self.track.display_text()}"


class TrackListModel(QAbstractListModel):
    CoverRole = Qt.UserRole + 1

    def __init__(self, tracks: List[Track] = None):
        super().__init__()
        self._tracks = tracks or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._tracks)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._tracks):
            return None
        track = self._tracks[index.row()]
        if role == Qt.DisplayRole:
            return track.display_text()
        elif role == self.CoverRole:
            return track.cover_uri
        elif role == Qt.UserRole:
            return track
        return None

    def addTrack(self, track: Track):
        self.beginInsertRows(QModelIndex(), len(self._tracks), len(self._tracks))
        self._tracks.append(track)
        self.endInsertRows()

    def removeTrack(self, index: int):
        if 0 <= index < len(self._tracks):
            self.beginRemoveRows(QModelIndex(), index, index)
            del self._tracks[index]
            self.endRemoveRows()

    def clear(self):
        self.beginResetModel()
        self._tracks.clear()
        self.endResetModel()

    def tracks(self) -> List[Track]:
        return self._tracks


class HistoryListModel(QAbstractListModel):
    """Модель для отображения истории прослушивания"""
    def __init__(self, entries: List[HistoryEntry] = None):
        super().__init__()
        self._entries = entries or []

    def rowCount(self, parent=QModelIndex()) -> int:
        return len(self._entries)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._entries):
            return None
        entry = self._entries[index.row()]
        if role == Qt.DisplayRole:
            return entry.display_text()
        elif role == Qt.UserRole:
            return entry.track
        return None

    def add_entry(self, entry: HistoryEntry):
        self.beginInsertRows(QModelIndex(), len(self._entries), len(self._entries))
        self._entries.append(entry)
        self.endInsertRows()

    def clear(self):
        self.beginResetModel()
        self._entries.clear()
        self.endResetModel()