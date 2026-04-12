import sys

import dotenv
from PySide6.QtWidgets import QApplication
from PySide6.QtCore import QFile, QTextStream
from gui.main_window import MainWindow


def main():
    app = QApplication(sys.argv)

    # Загрузка стилей
    file = QFile("style.qss")
    if file.open(QFile.ReadOnly | QFile.Text):
        stream = QTextStream(file)
        app.setStyleSheet(stream.readAll())

    window = MainWindow()
    window.show()
    sys.exit(app.exec())


if __name__ == "__main__":
    dotenv.load_dotenv()
    main()