from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox,
    QLabel, QPushButton, QHBoxLayout, QMessageBox
)
from PySide6.QtCore import Qt
from utils.server_client import ServerClient


class ServerTrackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Получить трек с сервера")
        self.setFixedSize(500, 210)

        self.server_client = ServerClient()
        self.server_client.requestFinished.connect(self._on_response)
        self.server_client.errorOccurred.connect(self._on_error)

        self.selected_url = None

        layout = QVBoxLayout()
        layout.setSpacing(15)

        title = QLabel("Введите URL аудиофайла или API эндпоинт")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("dialogTitle")
        layout.addWidget(title)

        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("https://example.com/api/track или прямая ссылка на mp3")
        layout.addWidget(self.url_edit)

        # Кнопка получения трека
        self.fetch_btn = QPushButton("🔍 Получить трек")
        self.fetch_btn.setObjectName("primaryButton")
        self.fetch_btn.clicked.connect(self._fetch_track)
        layout.addWidget(self.fetch_btn)

        self.status_label = QLabel("")
        self.status_label.setAlignment(Qt.AlignCenter)
        self.status_label.setObjectName("statusLabel")
        layout.addWidget(self.status_label)

        # Стандартные кнопки OK/Cancel
        self.button_box = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.button_box.accepted.connect(self.accept)
        self.button_box.rejected.connect(self.reject)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)  # Изначально неактивна
        layout.addWidget(self.button_box)

        self.setLayout(layout)

    def _fetch_track(self):
        url = self.url_edit.text().strip()
        if not url:
            QMessageBox.warning(self, "Ошибка", "Введите URL")
            return

        # Прямая ссылка на аудиофайл
        if any(url.lower().endswith(ext) for ext in ['.mp3', '.wav', '.ogg', '.flac', '.m4a']):
            self.selected_url = url
            self.status_label.setText("✅ Прямая ссылка готова к воспроизведению")
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
            return

        # API запрос
        self.fetch_btn.setEnabled(False)
        self.button_box.button(QDialogButtonBox.Ok).setEnabled(False)
        self.status_label.setText("Получение данных с сервера...")
        self.server_client.GET(url)

    def _on_response(self, data, success):
        self.fetch_btn.setEnabled(True)

        if not success:
            self.status_label.setText("❌ Ошибка получения данных")
            return

        track = data
        track_url = track["URL"]
        print(track_url)

        if track_url:
            self.selected_url = track_url
            self.status_label.setText("✅ Трек получен, нажмите OK для воспроизведения")
            self.button_box.button(QDialogButtonBox.Ok).setEnabled(True)
        else:
            self.status_label.setText("⚠️ URL трека не найден в ответе")
            QMessageBox.information(self, "Информация",
                                    "В ответе сервера не найден URL аудиофайла.\n"
                                    "Попробуйте указать прямую ссылку на mp3 файл.")

    def _on_error(self, error_msg):
        self.fetch_btn.setEnabled(True)
        self.status_label.setText(f"❌ {error_msg}")
        QMessageBox.warning(self, "Ошибка", error_msg)

    def get_url(self):
        return self.selected_url