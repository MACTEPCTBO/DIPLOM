from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QPushButton, QHBoxLayout, QScrollArea, QFrame
)
from PySide6.QtCore import Qt, Signal
from PySide6.QtGui import QPixmap, QIcon

class CurrentTrackPanel(QWidget):
    like_clicked = Signal()
    dislike_clicked = Signal()
    save_clicked = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setMaximumWidth(300)

        main_layout = QVBoxLayout()
        main_layout.setSpacing(10)

        # Информация о текущем треке
        self.cover_label = QLabel()
        self.cover_label.setFixedSize(200, 200)
        self.cover_label.setAlignment(Qt.AlignCenter)
        self.cover_label.setStyleSheet("background-color: #333; border: 1px solid #555;")
        self.cover_label.setText("Обложка")
        main_layout.addWidget(self.cover_label, alignment=Qt.AlignCenter)

        self.title_label = QLabel("Нет трека")
        self.title_label.setAlignment(Qt.AlignCenter)
        self.title_label.setWordWrap(True)
        main_layout.addWidget(self.title_label)

        self.artist_label = QLabel("")
        self.artist_label.setAlignment(Qt.AlignCenter)
        main_layout.addWidget(self.artist_label)

        # Кнопки действий
        btn_layout = QHBoxLayout()
        self.like_btn = QPushButton("👍")
        self.like_btn.setToolTip("Нравится")
        self.like_btn.setEnabled(False)
        self.like_btn.clicked.connect(self.like_clicked)

        self.dislike_btn = QPushButton("👎")
        self.dislike_btn.setToolTip("Не нравится")
        self.dislike_btn.setEnabled(False)
        self.dislike_btn.clicked.connect(self.dislike_clicked)

        self.save_btn = QPushButton("💾")
        self.save_btn.setToolTip("Сохранить на ПК")
        self.save_btn.setEnabled(False)
        self.save_btn.clicked.connect(self.save_clicked)

        btn_layout.addWidget(self.like_btn)
        btn_layout.addWidget(self.dislike_btn)
        btn_layout.addWidget(self.save_btn)
        main_layout.addLayout(btn_layout)

        # Разделитель
        line = QFrame()
        line.setFrameShape(QFrame.HLine)
        line.setFrameShadow(QFrame.Sunken)
        main_layout.addWidget(line)

        # История (скроллируемая область)
        history_label = QLabel("<b>История прослушивания</b>")
        main_layout.addWidget(history_label)

        self.history_list = QVBoxLayout()
        self.history_widget = QWidget()
        self.history_widget.setLayout(self.history_list)

        scroll = QScrollArea()
        scroll.setWidgetResizable(True)
        scroll.setWidget(self.history_widget)
        main_layout.addWidget(scroll)

        self.setLayout(main_layout)

    def set_track_info(self, title, artist="", cover_data=None):
        self.title_label.setText(title)
        self.artist_label.setText(artist)
        if cover_data:
            pixmap = QPixmap()
            pixmap.loadFromData(cover_data)
            self.cover_label.setPixmap(pixmap.scaled(200, 200, Qt.KeepAspectRatio, Qt.SmoothTransformation))
        else:
            self.cover_label.clear()
            self.cover_label.setText("Обложка")

    def set_actions_enabled(self, enabled):
        self.like_btn.setEnabled(enabled)
        self.dislike_btn.setEnabled(enabled)
        self.save_btn.setEnabled(enabled)

    def add_history_entry(self, text):
        label = QLabel(text)
        label.setWordWrap(True)
        self.history_list.addWidget(label)

    def clear_history(self):
        # Удаляем все виджеты из лейаута истории
        while self.history_list.count():
            item = self.history_list.takeAt(0)
            if item.widget():
                item.widget().deleteLater()