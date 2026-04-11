from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout
from PySide6.QtCore import Qt
from PySide6.QtGui import QPixmap, QIcon

class TrackInfoPanel(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        layout.setSpacing(5)

        # Обложка (заглушка)
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(150, 150)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #333; border: 1px solid #555;")
        self.cover_label.setText("Обложка")
        layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)

        # Название трека
        self.title_label = QLabel("Нет трека")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        layout.addWidget(self.title_label)

        # Исполнитель
        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignCenter)
        layout.addWidget(self.artist_label)

        # Кнопки лайк/дизлайк/сохранить
        btn_layout = QHBoxLayout()
        self.like_button = QPushButton()
        self.like_button.setIcon(QIcon.fromTheme("emblem-favorite"))
        self.like_button.setText("👍")
        self.like_button.setToolTip("Нравится")
        self.like_button.setEnabled(False)

        self.dislike_button = QPushButton()
        self.dislike_button.setIcon(QIcon.fromTheme("emblem-unreadable"))
        self.dislike_button.setText("👎")
        self.dislike_button.setToolTip("Не нравится")
        self.dislike_button.setEnabled(False)

        self.save_button = QPushButton()
        self.save_button.setIcon(QIcon.fromTheme("document-save"))
        self.save_button.setText("💾")
        self.save_button.setToolTip("Сохранить на ПК")
        self.save_button.setEnabled(False)

        btn_layout.addWidget(self.like_button)
        btn_layout.addWidget(self.dislike_button)
        btn_layout.addWidget(self.save_button)
        layout.addLayout(btn_layout)

        self.setLayout(layout)

    def set_track_info(self, title, artist=""):
        self.title_label.setText(title)
        self.artist_label.setText(artist)