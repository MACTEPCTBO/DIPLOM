from PySide6.QtWidgets import (
    QMainWindow, QWidget, QVBoxLayout, QHBoxLayout, QSplitter, QMenuBar, QMenu,
    QFileDialog, QMessageBox, QStatusBar
)
from PySide6.QtCore import Qt, QUrl
from PySide6.QtMultimedia import QMediaMetaData

from core.player import AudioPlayer
from gui.player_controls import PlayerControls
from gui.playlist_view import PlaylistView
from gui.current_track_panel import CurrentTrackPanel
from gui.playlist_manager_panel import PlaylistManagerPanel
from gui.server_dialog import ServerTrackDialog
from utils.history_manager import HistoryManager
from utils.download_manager import DownloadManager


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Аудиоплеер")
        self.resize(1200, 700)

        # Применяем тёмную тему
        self._apply_dark_theme()

        self.player = AudioPlayer()
        self.playlist = self.player.playlist
        self.download_manager = DownloadManager()
        self.history_manager = HistoryManager()

        self._create_menu_bar()
        self._create_central_widget()
        self._create_status_bar()

        # Подключение сигналов
        self.player.trackFinished.connect(self._on_track_finished)
        self.player.errorOccurred.connect(self._show_error)
        self.player.metaDataChanged.connect(self._update_track_info)

        # Загрузка истории
        for title, source, timestamp in self.history_manager.get_history():
            self.current_track_panel.add_history_entry(f"[{timestamp}] {title}")

    def _apply_dark_theme(self):
        """Применяет тёмную тему в стиле Яндекс.Музыки."""
        dark_style = """
        QMainWindow {
            background-color: #1a1a1a;
        }
        QWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            font-family: 'Segoe UI', Arial, sans-serif;
        }
        QMenuBar {
            background-color: #2d2d2d;
            color: #ffffff;
            border-bottom: 1px solid #3d3d3d;
        }
        QMenuBar::item {
            background-color: transparent;
            padding: 6px 12px;
        }
        QMenuBar::item:selected {
            background-color: #3d3d3d;
            border-radius: 4px;
        }
        QMenu {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
        }
        QMenu::item {
            padding: 6px 30px 6px 20px;
        }
        QMenu::item:selected {
            background-color: #3d3d3d;
        }
        QPushButton {
            background-color: #2d2d2d;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 6px;
            padding: 8px 16px;
            font-size: 13px;
            font-weight: 500;
        }
        QPushButton:hover {
            background-color: #3d3d3d;
            border-color: #4d4d4d;
        }
        QPushButton:pressed {
            background-color: #252525;
        }
        QPushButton#primaryButton {
            background-color: #ffdb4d;
            color: #000000;
            border: none;
            font-weight: bold;
        }
        QPushButton#primaryButton:hover {
            background-color: #ffe066;
        }
        QPushButton#primaryButton:pressed {
            background-color: #ffd633;
        }
        QLabel#panelTitle {
            font-size: 14px;
            font-weight: bold;
            color: #b3b3b3;
            letter-spacing: 1px;
        }
        QLabel#separator {
            background-color: #3d3d3d;
        }
        QLabel#infoLabel {
            color: #999999;
            font-size: 12px;
            padding: 5px;
        }
        QTreeWidget {
            background-color: #1e1e1e;
            color: #ffffff;
            border: 1px solid #3d3d3d;
            border-radius: 8px;
            outline: none;
        }
        QTreeWidget::item {
            padding: 8px;
            border-bottom: 1px solid #2d2d2d;
        }
        QTreeWidget::item:hover {
            background-color: #2d2d2d;
        }
        QTreeWidget::item:selected {
            background-color: #3d3d3d;
        }
        QHeaderView::section {
            background-color: #252525;
            color: #b3b3b3;
            padding: 8px;
            border: none;
            border-right: 1px solid #3d3d3d;
            border-bottom: 1px solid #3d3d3d;
            font-weight: bold;
        }
        QSlider::groove:horizontal {
            height: 4px;
            background: #3d3d3d;
            border-radius: 2px;
        }
        QSlider::handle:horizontal {
            background: #ffdb4d;
            width: 16px;
            height: 16px;
            margin: -6px 0;
            border-radius: 8px;
        }
        QSlider::sub-page:horizontal {
            background: #ffdb4d;
            border-radius: 2px;
        }
        QScrollBar:vertical {
            background: #1e1e1e;
            width: 10px;
            border-radius: 5px;
        }
        QScrollBar::handle:vertical {
            background: #3d3d3d;
            border-radius: 5px;
            min-height: 20px;
        }
        QScrollBar::handle:vertical:hover {
            background: #4d4d4d;
        }
        QScrollBar::add-line:vertical, QScrollBar::sub-line:vertical {
            height: 0px;
        }
        QStatusBar {
            background-color: #252525;
            color: #999999;
            border-top: 1px solid #3d3d3d;
        }
        QFrame {
            border: none;
        }
        QFrame[frameShape="4"] {  /* HLine */
            background-color: #3d3d3d;
        }
        QFrame[frameShape="5"] {  /* VLine */
            background-color: #3d3d3d;
        }
        """
        self.setStyleSheet(dark_style)

    def _create_menu_bar(self):
        menubar = self.menuBar()

        file_menu = menubar.addMenu("Файл")
        file_menu.addAction("Открыть локальные файлы", self._open_local_files)
        file_menu.addSeparator()
        file_menu.addAction("Выход", self.close)

        server_menu = menubar.addMenu("Сервер")
        server_menu.addAction("Воспроизвести с сервера", self._play_server_track)

        help_menu = menubar.addMenu("Справка")
        help_menu.addAction("О программе", self._about)

    def _create_central_widget(self):
        central = QWidget()
        self.setCentralWidget(central)
        main_layout = QVBoxLayout(central)
        main_layout.setContentsMargins(5, 5, 5, 5)
        main_layout.setSpacing(5)

        # Горизонтальный сплиттер
        h_splitter = QSplitter(Qt.Horizontal)

        # Сначала создаём все виджеты
        self.playlist_view = PlaylistView(self.playlist, self.player)
        self.playlist_manager_panel = PlaylistManagerPanel(self.playlist, self.playlist_view)
        self.current_track_panel = CurrentTrackPanel()

        # Устанавливаем objectName после создания
        self.playlist_manager_panel.setObjectName("leftPanel")
        self.playlist_view.setObjectName("centerPanel")
        self.current_track_panel.setObjectName("rightPanel")

        # Добавляем в сплиттер
        h_splitter.addWidget(self.playlist_manager_panel)
        h_splitter.addWidget(self.playlist_view)
        h_splitter.addWidget(self.current_track_panel)

        h_splitter.setSizes([220, 680, 280])

        main_layout.addWidget(h_splitter, stretch=1)

        # Подключаем сигналы для панели текущего трека
        self.current_track_panel.like_clicked.connect(self._on_like)
        self.current_track_panel.dislike_clicked.connect(self._on_dislike)
        self.current_track_panel.save_clicked.connect(self._on_save_track)

        # Нижняя панель управления
        self.controls = PlayerControls(self.player)
        self.controls.setObjectName("bottomPanel")
        main_layout.addWidget(self.controls)

    def _create_status_bar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов к воспроизведению")

    def _open_local_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите аудиофайлы", "",
            "Аудио (*.mp3 *.wav *.flac *.ogg *.m4a);;Все файлы (*.*)"
        )
        for file in files:
            self.playlist.addMedia(QUrl.fromLocalFile(file))
        self.playlist_view.update_display()

    def _play_server_track(self):
        dialog = ServerTrackDialog(self)
        if dialog.exec():
            url = dialog.get_url()
            if url:
                self.player.set_media(url, is_local=False)
                self.player.play()
                self.current_server_url = url
                self.current_track_panel.set_actions_enabled(True)
                self.statusBar().showMessage(f"Воспроизведение: {url}")

    def _on_track_finished(self, title, source):
        self.history_manager.add_entry(title, source)
        self.current_track_panel.add_history_entry(f"[{self._current_time()}] {title}")
        self.current_track_panel.set_actions_enabled(False)
        self.statusBar().showMessage(f"Завершено: {title}")

    def _current_time(self):
        from datetime import datetime
        return datetime.now().strftime("%H:%M")

    def _update_track_info(self, metadata):
        title = metadata.get(QMediaMetaData.Title, self.player.current_media_info()[0])
        artist = metadata.get(QMediaMetaData.Author, "Неизвестен")

        cover = None
        if QMediaMetaData.ThumbnailImage in metadata:
            cover = metadata[QMediaMetaData.ThumbnailImage]
        elif QMediaMetaData.CoverArtImage in metadata:
            cover = metadata[QMediaMetaData.CoverArtImage]

        self.current_track_panel.set_track_info(title, artist, cover)

        source = self.player.current_media_info()[1]
        is_server = source.startswith('http://') or source.startswith('https://')
        self.current_track_panel.set_actions_enabled(is_server)
        if is_server:
            self.current_server_url = source
            self.statusBar().showMessage(f"Серверный трек: {title}")

    def _on_like(self):
        title, source = self.player.current_media_info()
        self.history_manager.add_rating(source, "like")
        self.statusBar().showMessage(f"👍 Понравилось: {title}", 2000)

    def _on_dislike(self):
        title, source = self.player.current_media_info()
        self.history_manager.add_rating(source, "dislike")
        self.statusBar().showMessage(f"👎 Не понравилось: {title}", 2000)

    def _on_save_track(self):
        if hasattr(self, 'current_server_url'):
            url = self.current_server_url
            self.statusBar().showMessage(f"Скачивание...")
            self.download_manager.download(url, self._on_download_finished)

    def _on_download_finished(self, success, file_path):
        if success:
            self.statusBar().showMessage(f"✅ Сохранено: {file_path}")
            QMessageBox.information(self, "Успех", f"Трек сохранён в:\n{file_path}")
        else:
            self.statusBar().showMessage("❌ Ошибка сохранения")
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить файл")

    def _show_error(self, error_msg):
        QMessageBox.warning(self, "Ошибка воспроизведения", error_msg)
        self.statusBar().showMessage(f"❌ Ошибка: {error_msg}")

    def _about(self):
        QMessageBox.about(self, "О программе",
                          "🎵 Аудиоплеер\n\n"
                          "Поддержка локальных и серверных треков.\n"
                          "Создание и управление плейлистами.\n"
                          "PySide6 + QtMultimedia\n\n"
                          "Дизайн в стиле Яндекс.Музыки")