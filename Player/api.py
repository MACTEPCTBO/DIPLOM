import json
from typing import List, Optional
from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
from models import Track
from storage import TokenStorage

SERVER_URL = "http://192.168.1.105:8000"
API_PREFIX = "/api/server"

class ServerAPI(QObject):
    login_success = Signal(str, str)  # access_token, refresh_token
    login_failed = Signal(str)
    search_finished = Signal(list)    # list of Track
    search_failed = Signal(str)
    token_refreshed = Signal(str, str)

    def __init__(self, base_url: str = SERVER_URL):
        super().__init__()
        self.base_url = base_url.rstrip('/')
        self.access_token: Optional[str] = None
        self.refresh_token: Optional[str] = None
        self.nam = QNetworkAccessManager()
        self.nam.finished.connect(self._handle_reply)
        self._pending_requests = {}
        self.storage = TokenStorage()

        # Попытка загрузить сохранённые токены
        tokens = self.storage.load_tokens()
        if tokens:
            self.access_token = tokens["access_token"]
            self.refresh_token = tokens["refresh_token"]

    def set_tokens(self, access: str, refresh: str):
        self.access_token = access
        self.refresh_token = refresh
        self.storage.save_tokens(access, refresh)
        print(access, refresh)


    def login(self, login: str, password: str):
        url = f"{self.base_url}{API_PREFIX}/user/login"
        req = QNetworkRequest(QUrl(url))
        req.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")
        data = json.dumps({"Login": login, "Password": password}).encode()
        reply = self.nam.post(req, data)
        self._pending_requests[reply] = ("login", None)
        

    def search_tracks(self, query: str):
        if not self.access_token:
            self.search_failed.emit("Not authenticated")
            return
        url = f"{self.base_url}{API_PREFIX}/track/{query}"
        req = QNetworkRequest(QUrl(url))
        req.setRawHeader(b"Authorization", f"Bearer {self.access_token}".encode())
        reply = self.nam.get(req)
        self._pending_requests[reply] = ("search", None)

    def _handle_reply(self, reply: QNetworkReply):
        if reply not in self._pending_requests:
            return
        req_type, _ = self._pending_requests.pop(reply)
        if reply.error() != QNetworkReply.NoError:
            err_msg = reply.errorString()
            if req_type == "login":
                self.login_failed.emit(err_msg)
            elif req_type == "search":
                self.search_failed.emit(err_msg)
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
                self.login_success.emit(access, refresh)
            else:
                self.login_failed.emit("Invalid server response")
        elif req_type == "search":
            tracks = self._parse_search_response(json_data)
            self.search_finished.emit(tracks)
        reply.deleteLater()

    def _parse_search_response(self, data) -> List[Track]:
        if not data:
            return []
        if isinstance(data, dict):
            data = [data]
        tracks = []
        for item in data:
            track = Track(
                id=item.get("Id"),
                title=item.get("Name", "Unknown"),
                artist=self._extract_artist(item),
                duration_ms=item.get("DurationMs", 0),
                url="",
                is_local=False,
                server_id=item.get("Id"),
                album=str(item.get("Albums", "")),
                cover_uri=self.get_full_cover_url(item.get("URI", ""))
            )
            tracks.append(track)
        return tracks

    def _extract_artist(self, item: dict) -> str:
        artists = item.get("Artists")
        if isinstance(artists, list) and artists:
            first = artists[0]
            if isinstance(first, dict):
                return first.get("Name", "Unknown Artist")
            else:
                return str(first)
        elif isinstance(artists, int):
            return f"Artist ID {artists}"
        return "Unknown Artist"

    def get_stream_url(self, server_id: int) -> str:
        return f"{self.base_url}{API_PREFIX}/track/listen/{server_id}"

    def get_full_cover_url(self, uri: str) -> str:
        if not uri:
            return ""
        if uri.startswith("http"):
            return uri
        # Предполагаем, что URI относительный от базового URL сервера
        return f"{self.base_url}{uri}"



    def clear_tokens(self):
        self.access_token = None
        self.refresh_token = None
        self.storage.clear_tokens()