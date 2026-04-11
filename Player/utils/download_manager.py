from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply
import os

class DownloadManager(QObject):
    finished = Signal(bool, str)  # success, file_path

    def __init__(self, parent=None):
        super().__init__(parent)
        self.manager = QNetworkAccessManager()
        self.current_reply = None

    def download(self, url, callback=None):
        self.url = url
        self.callback = callback
        request = QNetworkRequest(QUrl(url))
        self.current_reply = self.manager.get(request)
        self.current_reply.finished.connect(self._download_finished)

    def _download_finished(self):
        reply = self.current_reply
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            # Определяем имя файла из URL
            file_name = os.path.basename(QUrl(self.url).path())
            if not file_name:
                file_name = "downloaded_track.mp3"
            # Сохраняем в папку Downloads или в текущую директорию
            save_path = os.path.join(os.path.expanduser("~"), "Downloads", file_name)
            try:
                with open(save_path, "wb") as f:
                    f.write(data)
                self.finished.emit(True, save_path)
                if self.callback:
                    self.callback(True, save_path)
            except Exception as e:
                self.finished.emit(False, str(e))
                if self.callback:
                    self.callback(False, str(e))
        else:
            self.finished.emit(False, reply.errorString())
            if self.callback:
                self.callback(False, reply.errorString())
        reply.deleteLater()