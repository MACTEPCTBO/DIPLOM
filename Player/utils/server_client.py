import os

from PySide6.QtCore import QObject, Signal, QUrl, QUrlQuery
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import json

# Если у вас есть файл setting.py с константами API и IP, импортируйте их.
# Иначе задайте значения по умолчанию.
try:
    from setting import API, IP
except ImportError:
    API = "/api"       # значение по умолчанию
    IP = "localhost"   # значение по умолчанию


class ServerClient(QObject):
    requestFinished = Signal(dict, bool)  # data, success
    errorOccurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager()
        self._auth_token = os.getenv('TOKEN_AUTH')
        print(self._auth_token)
        self._token_type = "Bearer"
        self.baseURL = "http://" + IP + API


    def _add_auth_header(self, request: QNetworkRequest):
        """Добавляет заголовок Authorization, если установлен токен."""
        if self._auth_token:
            auth_value = f"{self._token_type} {self._auth_token}"
            request.setRawHeader(b"Authorization", auth_value.encode("utf-8"))

    def GET(self, url: str, params: dict = None, headers: dict = None):
        """Выполняет GET-запрос."""
        # Формируем URL с параметрами
        qurl = QUrl(url)
        if params:
            query = QUrlQuery()
            for key, value in params.items():
                query.addQueryItem(key, str(value))
            qurl.setQuery(query)

        request = QNetworkRequest(qurl)
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        if headers:
            for key, value in headers.items():
                request.setRawHeader(key.encode('utf-8'), str(value).encode('utf-8'))

        self._add_auth_header(request)

        self.current_reply = self.manager.get(request)
        self.current_reply.finished.connect(self._on_reply_finished)

    def POST(self, url: str, json_data: dict = None, headers: dict = None):
        """Выполняет POST-запрос с JSON-данными."""
        request = QNetworkRequest(QUrl(url))
        request.setHeader(QNetworkRequest.ContentTypeHeader, "application/json")

        if headers:
            for key, value in headers.items():
                request.setRawHeader(key.encode('utf-8'), str(value).encode('utf-8'))

        post_data = None
        if json_data:
            post_data = json.dumps(json_data, ensure_ascii=False).encode('utf-8')

        self._add_auth_header(request)

        self.current_reply = self.manager.post(request, post_data)
        self.current_reply.finished.connect(self._on_reply_finished)

    def _on_reply_finished(self):
        reply = self.sender()
        if reply.error() == QNetworkReply.NoError:
            try:
                data = reply.readAll().data().decode('utf-8')
                json_data = json.loads(data)
                self.requestFinished.emit(json_data, True)
            except Exception as e:
                self.errorOccurred.emit(f"Ошибка парсинга JSON: {str(e)}")
                self.requestFinished.emit({}, False)
        else:
            self.errorOccurred.emit(f"Ошибка сети: {reply.errorString()}")
            self.requestFinished.emit({}, False)
        reply.deleteLater()