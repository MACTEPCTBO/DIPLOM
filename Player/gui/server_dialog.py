from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox,
    QLabel, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from utils.server_client import GetServerClient


class ServerTrackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Получить трек с сервера")
        self.setFixedSize(500, 150)

        self.get_client = GetServerClient()
        self.get_client.requestFinished.connect(self._on_response)
        self.get_client.errorOccurred.connect(self._on_error)

        self.selected_url = None

        layout = QVBoxLayout()
        layout.setSpacing(15)

        # Заголовок
        title = QLabel("Введите URL аудиофайла или API эндпоинт")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        # Поле ввода
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/api/track или прямая ссылка на mp3")
        layout.addWidget(self.url_edit)

        # Кнопки
        button_layout = QHBoxLayout()

        self.fetch_btn = QPushButton("🔍 Получить трек")
        self.fetch_btn.setObjectName("primaryButton")
        self.fetch_btn.clicked.connect(self._fetch_track)

        cancel_btn = QPushButton("Отмена")
        cancel_btn.clicked.connect(self.reject)

        button_layout.addWidget(self.fetch_btn)
        button_layout.addWidget(cancel_btn)
        layout.addLayout(button_layout)

        # Статус
        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        self.setLayout(layout)

    def _fetch_track(self):
        """Получение трека с сервера."""
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL")
            return

        # Проверяем, является ли URL прямой ссылкой на аудио
        if any(url.lower().endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']):
            self.selected_url = url
            self.accept()
            return

        # Иначе считаем, что это API и делаем GET-запрос
        self.fetch_btn.setEnabled(False)
        self.status_label.setText("Получение данных с сервера...")
        self.get_client.send_request(url)

    def _on_response(self, data, success):
        """Обработка ответа от API."""
        self.fetch_btn.setEnabled(True)

        if not success:
            self.status_label.setText("❌ Ошибка получения данных")
            return

        # Ищем URL трека в ответе (может быть в разных полях)
        track_url = None
        if isinstance(data, dict):
            # Проверяем возможные поля с URL
            for field in ['url', 'track_url', 'audio_url', 'file', 'source']:
                if field in data and isinstance(data[field], str):
                    track_url = data[field]
                    break

        if track_url:
            self.selected_url = track_url
            self.status_label.setText("✅ Трек получен, нажмите OK для воспроизведения")
        else:
            self.status_label.setText("⚠️ URL трека не найден в ответе")
            QMessageBox.information(self, "Информация",
                                    "В ответе сервера не найден URL аудиофайла.\n"
                                    "Попробуйте указать прямую ссылку на mp3 файл.")

    def _on_error(self, error_msg):
        """Обработка ошибок сети."""
        self.fetch_btn.setEnabled(True)
        self.status_label.setText(f"❌ {error_msg}")
        QMessageBox.warning(self, "Ошибка", error_msg)

    def get_url(self):
        """Возвращает URL трека для воспроизведения."""
        return self.selected_url