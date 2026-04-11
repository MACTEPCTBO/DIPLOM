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

        # Горизонтальный сплиттер для левой панели, центра и правой панели
        h_splitter = QSplitter(Qt.Horizontal)

        # Левая панель: управление плейлистами
        self.playlist_view = PlaylistView(self.playlist, self.player)
        self.playlist_manager_panel = PlaylistManagerPanel(self.playlist, self.playlist_view)
        h_splitter.addWidget(self.playlist_manager_panel)

        # Центральная панель: визуализация плейлиста
        h_splitter.addWidget(self.playlist_view)

        # Правая панель: информация о треке + история
        self.current_track_panel = CurrentTrackPanel()
        self.current_track_panel.like_clicked.connect(self._on_like)
        self.current_track_panel.dislike_clicked.connect(self._on_dislike)
        self.current_track_panel.save_clicked.connect(self._on_save_track)
        h_splitter.addWidget(self.current_track_panel)

        h_splitter.setSizes([200, 600, 300])  # начальные размеры

        main_layout.addWidget(h_splitter, stretch=1)

        # Нижняя панель управления воспроизведением
        self.controls = PlayerControls(self.player)
        main_layout.addWidget(self.controls)

    def _create_status_bar(self):
        self.setStatusBar(QStatusBar())
        self.statusBar().showMessage("Готов")

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

    def _on_track_finished(self, title, source):
        self.history_manager.add_entry(title, source)
        self.current_track_panel.add_history_entry(f"[{self._current_time()}] {title}")
        self.current_track_panel.set_actions_enabled(False)

    def _current_time(self):
        from datetime import datetime
        return datetime.now().strftime("%Y-%m-%d %H:%M:%S")

    def _update_track_info(self, metadata):
        title = metadata.get(QMediaMetaData.Title, self.player.current_media_info()[0])
        artist = metadata.get(QMediaMetaData.Author, "Неизвестен")
        # Попытка извлечь обложку из метаданных
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
            self.statusBar().showMessage(f"Скачивание {url}...")
            self.download_manager.download(url, self._on_download_finished)

    def _on_download_finished(self, success, file_path):
        if success:
            self.statusBar().showMessage(f"Сохранено: {file_path}")
        else:
            QMessageBox.warning(self, "Ошибка", f"Не удалось сохранить файл:\n{file_path}")

    def _show_error(self, error_msg):
        QMessageBox.warning(self, "Ошибка воспроизведения", error_msg)

    def _about(self):
        QMessageBox.about(self, "О программе",
                          "Аудиоплеер с поддержкой локальных и серверных треков.\n"
                          "PySide6 + QtMultimedia")