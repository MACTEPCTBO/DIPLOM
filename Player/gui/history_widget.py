from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel
)
from PySide6.QtCore import Qt
from datetime import datetime

class HistoryWidget(QWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        layout = QVBoxLayout()
        self.label = QLabel("История воспроизведения")
        layout.addWidget(self.label)
        self.list_widget = QListWidget()
        layout.addWidget(self.list_widget)
        self.setLayout(layout)

    def add_entry(self, title, source):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        display_text = f"[{timestamp}] {title}"
        item = QListWidgetItem(display_text)
        item.setData(Qt.UserRole, (title, source, timestamp))
        self.list_widget.insertItem(0, item)  # в начало

    def load_history(self, entries):
        """Загружает список записей из менеджера истории."""
        for title, source, timestamp in entries:
            display_text = f"[{timestamp}] {title}"
            item = QListWidgetItem(display_text)
            item.setData(Qt.UserRole, (title, source, timestamp))
            self.list_widget.addItem(item)