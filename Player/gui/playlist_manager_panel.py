from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt, QUrl

class PlaylistManagerPanel(QWidget):
    def __init__(self, playlist_manager, playlist_widget, parent=None):
        super().__init__(parent)
        self.playlist = playlist_manager
        self.playlist_widget = playlist_widget

        layout = QVBoxLayout()
        layout.setSpacing(10)
        layout.setContentsMargins(10, 10, 10, 10)

        # Заголовок
        title = QLabel("УПРАВЛЕНИЕ ПЛЕЙЛИСТОМ")
        title.setAlignment(Qt.AlignCenter)
        title.setObjectName("panelTitle")
        layout.addWidget(title)

        # Кнопка добавления треков
        self.add_btn = QPushButton("➕ Добавить треки")
        self.add_btn.setObjectName("primaryButton")
        self.add_btn.clicked.connect(self._add_tracks)
        layout.addWidget(self.add_btn)

        # Разделитель
        separator = QLabel()
        separator.setFixedHeight(1)
        separator.setObjectName("separator")
        layout.addWidget(separator)

        # Остальные кнопки
        self.new_btn = QPushButton("📝 Новый плейлист")
        self.new_btn.clicked.connect(self._new_playlist)
        layout.addWidget(self.new_btn)

        self.load_btn = QPushButton("📂 Загрузить плейлист")
        self.load_btn.clicked.connect(self._load_playlist)
        layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("💾 Сохранить плейлист")
        self.save_btn.clicked.connect(self._save_playlist)
        layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton("🗑️ Очистить плейлист")
        self.clear_btn.clicked.connect(self._clear_playlist)
        layout.addWidget(self.clear_btn)

        layout.addStretch()

        # Информация о количестве треков
        self.info_label = QLabel("Треков: 0")
        self.info_label.setAlignment(Qt.AlignCenter)
        self.info_label.setObjectName("infoLabel")
        layout.addWidget(self.info_label)

        self.setLayout(layout)

        # Обновление счётчика треков
        self.playlist.playlistChanged.connect(self._update_track_count)

    def _add_tracks(self):
        """Добавление локальных треков в плейлист."""
        files, _ = QFileDialog.getOpenFileNames(
            self,
            "Выберите аудиофайлы",
            "",
            "Аудио (*.mp3 *.wav *.flac *.ogg *.m4a);;Все файлы (*.*)"
        )
        for file in files:
            self.playlist.addMedia(QUrl.fromLocalFile(file))
        self.playlist_widget.update_display()

    def _new_playlist(self):
        self.playlist.clear()
        self.playlist_widget.update_display()
        QMessageBox.information(self, "Плейлист", "Создан новый пустой плейлист.")

    def _load_playlist(self):
        file_path, _ = QFileDialog.getOpenFileName(
            self, "Загрузить плейлист", "", "Плейлист (*.json)"
        )
        if file_path:
            try:
                self.playlist_widget.load_playlist(file_path)
                QMessageBox.information(self, "Успех", "Плейлист загружен.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить плейлист:\n{e}")

    def _save_playlist(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить плейлист", "", "Плейлист (*.json)"
        )
        if file_path:
            if not file_path.endswith('.json'):
                file_path += '.json'
            try:
                self.playlist_widget.save_playlist(file_path)
                QMessageBox.information(self, "Успех", "Плейлист сохранён.")
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить плейлист:\n{e}")

    def _clear_playlist(self):
        reply = QMessageBox.question(
            self, "Подтверждение",
            "Вы уверены, что хотите очистить плейлист?",
            QMessageBox.Yes | QMessageBox.No
        )
        if reply == QMessageBox.Yes:
            self.playlist.clear()
            self.playlist_widget.update_display()

    def _update_track_count(self):
        count = self.playlist.mediaCount()
        self.info_label.setText(f"Треков: {count}")