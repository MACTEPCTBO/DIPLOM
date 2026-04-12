from PySide6.QtCore import Qt, QAbstractListModel, QModelIndex
from dataclasses import dataclass, field
from typing import List, Optional, Dict, Any

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

    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "type": self.playlist_type,
            "tracks": [t.to_dict() for t in self.tracks]
        }

    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> 'Playlist':
        tracks = [Track.from_dict(t) for t in data.get("tracks", [])]
        return cls(name=data["name"], tracks=tracks, playlist_type=data.get("type", "local"))

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