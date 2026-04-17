# api.py
import json
from typing import List, Optional, Dict, Any
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from models import Track, Playlist
import sqlite3
from pathlib import Path

SERVER_URL = "http://192.168.1.105:8000"
API_PREFIX = "/api/server"  # Исправлено на /api вместо /api/server


class TokenStorage:
    def __init__(self):
        self.db_path = Path("tokens.db")
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                CREATE TABLE IF NOT EXISTS tokens (
                    id INTEGER PRIMARY KEY CHECK (id = 1),
                    access_token TEXT NOT NULL,
                    refresh_token TEXT NOT NULL,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

    def save_tokens(self, access: str, refresh: str):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("""
                INSERT OR REPLACE INTO tokens (id, access_token, refresh_token, updated_at)
                VALUES (1, ?, ?, CURRENT_TIMESTAMP)
            """, (access, refresh))

    def load_tokens(self):
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.execute("SELECT access_token, refresh_token FROM tokens WHERE id = 1")
            row = cursor.fetchone()
            if row:
                return row[0], row[1]
        return None, None

    def clear_tokens(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM tokens WHERE id = 1")


class ServerAPI(QObject):
    login_success = Signal(str, str)
    login_failed = Signal(str)
    search_finished = Signal(list)
    search_failed = Signal(str)
    playlist_loaded = Signal(Playlist)
    playlist_load_failed = Signal(str)
    like_status_changed = Signal(bool)
    radio_stations_loaded = Signal(list)
    token_refreshed = Signal(str, str)

    def __init__(self, base_url: str = SERVER_URL):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self._handle_reply)
        self._pending_requests = {}  # reply -> (type, retry_info)
        self.token_storage = TokenStorage()
        tokens = self.token_storage.load_tokens()
        if tokens:
            self.access_token = tokens[0]
            self.refresh_token = tokens[1]

    def set_tokens(self, access: str, refresh: str):
        self.access_token = access
        self.refresh_token = refresh
        self.token_storage.save_tokens(access, refresh)

    def clear_tokens(self):
        self.access_token = None
        self.refresh_token = None
        self.token_storage.clear_tokens()

    def _add_auth_header(self, request: QNetworkRequest):
        if self.access_token:
            request.setRawHeader(b"Authorization", f"Bearer {self.access_token}".encode())

    def _make_request(self, method: str, url: str, req_type: str, data: Optional[bytes] = None):
        req = QNetworkRequest(QUrl(url))
        if method.upper() == "POST":
            req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        self._add_auth_header(req)
        if method.upper() == "GET":
            reply = self.nam.get(req)
        else:
            reply = self.nam.post(req, data or b"")
        self._pending_requests[reply] = (req_type, {
            "method": method,
            "url": url,
            "data": data,
            "req_type": req_type  # сохраняем тип для повтора
        })

    def login(self, login: str, password: str):
        url = f"{self.base_url}{API_PREFIX}/user/login"
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        data = json.dumps({"Login": login, "Password": password}).encode()
        reply = self.nam.post(req, data)
        self._pending_requests[reply] = ("login", None)

    def refresh_token_request(self):
        if not self.refresh_token:
            return
        url = f"{self.base_url}{API_PREFIX}/user/refresh"
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        data = json.dumps({"Token": self.refresh_token}).encode()
        reply = self.nam.post(req, data)
        self._pending_requests[reply] = ("refresh", None)

    def search_tracks(self, query: str):
        if not self.access_token:
            self.search_failed.emit("Not authenticated")
            return
        url = f"{self.base_url}{API_PREFIX}/track/{query}"
        self._make_request("GET", url, "search")

    def get_likes_playlist(self):
        if not self.access_token:
            self.playlist_load_failed.emit("Not authenticated")
            return
        url = f"{self.base_url}{API_PREFIX}/track/playlist/likes/{self.access_token}/all"
        self._make_request("GET", url, "likes_playlist")

    def get_playlist_by_name(self, name: str):
        if not self.access_token:
            self.playlist_load_failed.emit("Not authenticated")
            return
        url = f"{self.base_url}{API_PREFIX}/track/playlist/{name}/{self.access_token}"
        self._make_request("GET", url, "playlist")

    def like_track(self, track_id: int, like: bool = True):
        if not self.access_token:
            self.like_status_changed.emit(False)
            return
        action = "add" if like else "remove"
        url = f"{self.base_url}{API_PREFIX}/track/rating/like/{action}"
        data = json.dumps({"Id": track_id}).encode()
        self._make_request("POST", url, "like", data)

    def dislike_track(self, track_id: int, dislike: bool = True):
        if not self.access_token:
            self.like_status_changed.emit(False)
            return
        action = "add" if dislike else "remove"
        url = f"{self.base_url}{API_PREFIX}/track/rating/dislike/{action}"
        data = json.dumps({"Id": track_id}).encode()
        self._make_request("POST", url, "dislike", data)

    def load_radio_stations(self):
        stations = [
            {
                "id": {"type": "genre", "tag": "pop"},
                "name": "Поп",
                "icon": {
                    "background_color": "#FF6665",
                    "image_url": "https://avatars.yandex.net/get-music-misc/34161/rotor-genre-pop-icon/%%"
                }
            },
            {
                "id": {"type": "genre", "tag": "rock"},
                "name": "Рок",
                "icon": {
                    "background_color": "#E62E2E",
                    "image_url": "https://avatars.yandex.net/get-music-misc/34161/rotor-genre-rock-icon/%%"
                }
            },
            {
                "id": {"type": "genre", "tag": "electronic"},
                "name": "Электроника",
                "icon": {
                    "background_color": "#8A2BE2",
                    "image_url": "https://avatars.yandex.net/get-music-misc/34161/rotor-genre-electronic-icon/%%"
                }
            }
        ]
        self.radio_stations_loaded.emit(stations)

    def _handle_reply(self, reply: QNetworkReply):
        if reply not in self._pending_requests:
            return
        req_type, retry_data = self._pending_requests.pop(reply)
        status_code = reply.attribute(QNetworkRequest.HttpStatusCodeAttribute)

        if status_code == 401 and req_type != "refresh" and self.refresh_token:
            # Сохраняем запрос для повтора и запускаем обновление токена
            self._pending_requests[reply] = (req_type, retry_data)
            self.refresh_token_request()
            reply.deleteLater()
            return

        if reply.error() != QNetworkReply.NoError:
            err_msg = reply.errorString()
            if req_type == "login":
                self.login_failed.emit(err_msg)
            elif req_type == "search":
                self.search_failed.emit(err_msg)
            elif req_type in ("likes_playlist", "playlist"):
                self.playlist_load_failed.emit(err_msg)
            elif req_type in ("like", "dislike"):
                self.like_status_changed.emit(False)
            elif req_type == "refresh":
                self.clear_tokens()
                self.login_failed.emit("Session expired. Please login again.")
            reply.deleteLater()
            return

        data = reply.readAll().data().decode()
        try:
            json_data = json.loads(data)
        except:
            json_data = None

        if req_type == "login":
            access = json_data.get("AccessToken")
            refresh = json_data.get("RefreshToken")
            if access and refresh:
                self.access_token = access
                self.refresh_token = refresh
                self.token_storage.save_tokens(access, refresh)
                self.login_success.emit(access, refresh)
            else:
                self.login_failed.emit("Invalid server response")

        elif req_type == "refresh":
            access = json_data.get("AccessToken")
            refresh = json_data.get("RefreshToken")
            if access and refresh:
                self.access_token = access
                self.refresh_token = refresh
                self.token_storage.save_tokens(access, refresh)
                self.token_refreshed.emit(access, refresh)
                # Повторяем исходный запрос, если он был
                if retry_data:
                    method = retry_data["method"]
                    url = retry_data["url"]
                    data = retry_data.get("data")
                    req_type_orig = retry_data.get("req_type", "unknown")
                    self._make_request(method, url, req_type_orig, data)
            else:
                self.clear_tokens()
                self.login_failed.emit("Token refresh failed")

        elif req_type == "search":
            tracks = self._parse_search_response(json_data)
            self.search_finished.emit(tracks)

        elif req_type in ("likes_playlist", "playlist"):
            playlist = self._parse_playlist_response(json_data)
            if playlist:
                self.playlist_loaded.emit(playlist)
            else:
                self.playlist_load_failed.emit("Failed to parse playlist")

        elif req_type in ("like", "dislike"):
            success = json_data if isinstance(json_data, bool) else False
            self.like_status_changed.emit(success)

        reply.deleteLater()

    def _parse_search_response(self, data) -> List[Track]:
        if not data:
            return []
        if isinstance(data, dict):
            data = [data]
        tracks = []
        for item in data:
            cover_uri = self.get_full_cover_url(item.get("URI", ""))
            artist_name = self._extract_artist_name(item)
            track = Track(
                id=item.get("Id"),
                title=item.get("Name", "Unknown"),
                artist=artist_name,
                duration_ms=item.get("DurationMs", 0) or item.get("Duration_ms", 0),
                url="",
                is_local=False,
                server_id=item.get("Id"),
                album=str(item.get("Albums", "")),
                cover_uri=cover_uri
            )
            tracks.append(track)
        return tracks

    def _parse_playlist_response(self, data) -> Optional[Playlist]:
        if not data:
            return None
        playlist_id = data.get("Id", 0)
        name = data.get("Name", "")
        count = data.get("Count", 0)
        tracks_data = data.get("Tracks", [])
        tracks = []
        for item in tracks_data:
            artist_name = self._extract_artist_name(item)
            track = Track(
                id=item.get("Id"),
                title=item.get("Name", "Unknown"),
                artist=artist_name,
                duration_ms=item.get("DurationMs", 0) or item.get("Duration_ms", 0),
                url="",
                is_local=False,
                server_id=item.get("Id"),
                cover_uri=self.get_full_cover_url(item.get("URI", ""))
            )
            tracks.append(track)
        return Playlist(
            id=playlist_id,
            name=name,
            tracks=tracks,
            playlist_type="server",
            count=count
        )

    def _extract_artist_name(self, item: dict) -> str:
        artists = item.get("Artists")
        if artists is None:
            return "Unknown Artist"
        if isinstance(artists, int):
            return f"Artist {artists}"
        if isinstance(artists, dict):
            return artists.get("Name", "Unknown Artist")
        if isinstance(artists, list) and artists:
            first = artists[0]
            if isinstance(first, dict):
                return first.get("Name", "Unknown Artist")
            elif isinstance(first, int):
                return f"Artist {first}"
        return "Unknown Artist"

    def get_full_cover_url(self, uri: str) -> str:
        if not uri:
            return ""
        if uri.startswith("http"):
            return uri
        return f"{self.base_url}{uri}"

    def get_stream_url(self, server_id: int) -> str:
        return f"{self.base_url}{API_PREFIX}/track/listen/{server_id}"