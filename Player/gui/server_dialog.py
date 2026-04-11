from PySide6.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QDialogButtonBox, QLabel
)

class ServerTrackDialog(QDialog):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setWindowTitle("Воспроизвести с сервера")
        layout = QVBoxLayout()

        layout.addWidget(QLabel("Введите URL аудиофайла:"))
        self.url_edit = QLineEdit()
        self.url_edit.setPlaceholderText("http://example.com/track.mp3")
        layout.addWidget(self.url_edit)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(self.accept)
        buttons.rejected.connect(self.reject)
        layout.addWidget(buttons)

        self.setLayout(layout)

    def get_url(self):
        return self.url_edit.text().strip()