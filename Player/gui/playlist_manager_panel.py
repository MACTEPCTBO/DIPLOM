from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QPushButton, QLabel, QFileDialog, QMessageBox
)
from PySide6.QtCore import Qt

class PlaylistManagerPanel(QWidget):
    def __init__(self, playlist_manager, playlist_widget, parent=None):
        super().__init__(parent)
        self.playlist = playlist_manager
        self.playlist_widget = playlist_widget

        layout = QVBoxLayout()
        layout.setSpacing(10)

        title = QLabel("<b>Управление плейлистом</b>")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.new_btn = QPushButton("Создать новый")
        self.new_btn.clicked.connect(self._new_playlist)
        layout.addWidget(self.new_btn)

        self.load_btn = QPushButton("Загрузить...")
        self.load_btn.clicked.connect(self._load_playlist)
        layout.addWidget(self.load_btn)

        self.save_btn = QPushButton("Сохранить...")
        self.save_btn.clicked.connect(self._save_playlist)
        layout.addWidget(self.save_btn)

        self.clear_btn = QPushButton("Очистить")
        self.clear_btn.clicked.connect(self._clear_playlist)
        layout.addWidget(self.clear_btn)

        layout.addStretch()
        self.setLayout(layout)

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
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось загрузить плейлист:\n{e}")

    def _save_playlist(self):
        file_path, _ = QFileDialog.getSaveFileName(
            self, "Сохранить плейлист", "", "Плейлист (*.json)"
        )
        if file_path:
            try:
                self.playlist_widget.save_playlist(file_path)
            except Exception as e:
                QMessageBox.critical(self, "Ошибка", f"Не удалось сохранить плейлист:\n{e}")

    def _clear_playlist(self):
        self.playlist.clear()
        self.playlist_widget.update_display()