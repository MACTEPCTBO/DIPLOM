import json
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QInputDialog, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QListWidgetItem,
    QStackedWidget, QStatusBar, QLabel
)
from PySide6.QtGui import QPalette, QColor

from models import Track, Playlist, TrackListModel
from api import ServerAPI
from player import AudioController
from widgets import NavigationPanel, SearchBar, PlaybackControls, PlaylistView

class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Player")
        self.resize(1100, 700)
        self._apply_dark_theme()

        # Инициализация компонентов
        self.api = ServerAPI()
        self.audio_controller = AudioController()
        self.track_model = TrackListModel()

        # Данные
        self.current_playlist: Optional[Playlist] = None
        self.current_track_index: int = -1
        self.local_playlists: List[Playlist] = []
        self.server_playlists: List[Playlist] = []
        self.playlists_dir = Path("playlists")
        self.playlists_dir.mkdir(exist_ok=True)

        self.auth_status = False

        self._setup_ui()
        self._connect_signals()
        self._load_playlists()

        # Таймер обновления UI
        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(200)

        self._check_auto_login()

    def _check_auto_login(self):
        """Проверяет, есть ли сохранённые токены, и обновляет статус."""
        print(self.api.access_token)
        if self.api.access_token:
            self.auth_status = True
            self.nav_panel.set_login_status(True)
            self.status_bar.showMessage("Автоматический вход выполнен", 3000)
        else:
            self.auth_status = False
            self.nav_panel.set_login_status(False)



    def _apply_dark_theme(self):
        palette = QPalette()
        palette.setColor(QPalette.Window, QColor(18, 18, 18))
        palette.setColor(QPalette.WindowText, Qt.white)
        palette.setColor(QPalette.Base, QColor(25, 25, 25))
        palette.setColor(QPalette.AlternateBase, QColor(53, 53, 53))
        palette.setColor(QPalette.ToolTipBase, Qt.black)
        palette.setColor(QPalette.ToolTipText, Qt.white)
        palette.setColor(QPalette.Text, Qt.white)
        palette.setColor(QPalette.Button, QColor(45, 45, 45))
        palette.setColor(QPalette.ButtonText, Qt.white)
        palette.setColor(QPalette.BrightText, Qt.red)
        palette.setColor(QPalette.Link, QColor(42, 130, 218))
        palette.setColor(QPalette.Highlight, QColor(42, 130, 218))
        palette.setColor(QPalette.HighlightedText, Qt.black)
        self.setPalette(palette)

    def _setup_ui(self):
        # Центральный виджет
        central = QWidget()
        self.setCentralWidget(central)
        v_main = QVBoxLayout(central)
        v_main.setContentsMargins(0, 0, 0, 0)
        v_main.setSpacing(0)

        # Горизонтальный контейнер для левой панели и стека
        h_content = QHBoxLayout()
        h_content.setSpacing(0)

        # Левая панель навигации
        self.nav_panel = NavigationPanel()
        h_content.addWidget(self.nav_panel)

        # Центральный стек
        self.stacked = QStackedWidget()
        h_content.addWidget(self.stacked, 1)

        v_main.addLayout(h_content, 1)

        # Нижняя панель управления
        self.controls = PlaybackControls()
        v_main.addWidget(self.controls)

        # Страница главного экрана (поиск и текущий плейлист)
        home_widget = QWidget()
        home_layout = QVBoxLayout(home_widget)
        home_layout.setContentsMargins(20, 20, 20, 0)
        home_layout.setSpacing(20)

        # Поиск сверху по центру
        search_container = QHBoxLayout()
        search_container.addStretch()
        self.search_bar = SearchBar()
        search_container.addWidget(self.search_bar)
        search_container.addStretch()
        home_layout.addLayout(search_container)

        # Отображение плейлиста
        self.playlist_view = PlaylistView(self.track_model)
        home_layout.addWidget(self.playlist_view, 1)

        self.stacked.addWidget(home_widget)

        # Страница локальных плейлистов (пока заглушка)
        local_pl_widget = QWidget()
        local_layout = QVBoxLayout(local_pl_widget)
        local_layout.addWidget(QLabel("Локальные плейлисты (в разработке)"))
        self.stacked.addWidget(local_pl_widget)

        # Страница серверных плейлистов
        server_pl_widget = QWidget()
        server_layout = QVBoxLayout(server_pl_widget)
        server_layout.addWidget(QLabel("Серверные плейлисты (в разработке)"))
        self.stacked.addWidget(server_pl_widget)

        # Статус бар
        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов")

    def _connect_signals(self):
        # Навигация
        self.nav_panel.login_clicked.connect(self._toggle_login)
        self.nav_panel.home_clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        self.nav_panel.local_playlists_clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        self.nav_panel.server_playlists_clicked.connect(lambda: self.stacked.setCurrentIndex(2))

        # Поиск
        self.search_bar.search_requested.connect(self._search_server)

        # Управление воспроизведением
        self.controls.play_clicked.connect(self.audio_controller.toggle_play_pause)
        self.controls.next_clicked.connect(self._next_track)
        self.controls.prev_clicked.connect(self._prev_track)
        self.controls.volume_changed.connect(self.audio_controller.set_volume)
        self.controls.position_changed.connect(self.audio_controller.set_position)

        # Плейлист
        self.playlist_view.track_selected.connect(self._play_track_at_index)
        # Подключаем кнопки из PlaylistView к методам главного окна
        self.playlist_view.btn_add_local.clicked.connect(self.add_local_files)
        self.playlist_view.btn_clear.clicked.connect(self.clear_playlist)
        self.playlist_view.btn_save.clicked.connect(self.save_current_playlist)
        self.playlist_view.btn_load.clicked.connect(self.load_playlist_dialog)

        # Аудио контроллер
        #self.audio_controller.position_changed.connect(self.controls.update_position)
        self.audio_controller.duration_changed.connect(self.controls.set_duration)
        self.audio_controller.state_changed.connect(self._on_player_state_changed)
        self.audio_controller.error_occurred.connect(lambda msg: QMessageBox.warning(self, "Ошибка", msg))
        self.audio_controller.track_changed.connect(self._on_track_changed)

        # Подключаем кнопки управления плейлистом из PlaylistView
        btn_add, btn_clear, btn_save, btn_load = self.playlist_view.get_buttons()
        btn_add.clicked.connect(self.add_local_files)
        btn_clear.clicked.connect(self.clear_playlist)
        btn_save.clicked.connect(self.save_current_playlist)
        btn_load.clicked.connect(self.load_playlist_dialog)

        # API
        self.api.login_success.connect(self._on_login_success)
        self.api.login_failed.connect(lambda msg: QMessageBox.critical(self, "Ошибка входа", msg))
        self.api.search_finished.connect(self._on_search_finished)
        self.api.search_failed.connect(lambda msg: QMessageBox.warning(self, "Поиск не удался", msg))

    def _on_track_changed(self, track: Track):
        """Обработчик смены трека: обновляет информацию в плейлисте"""
        self.playlist_view.set_current_track_info(
            title=track.title,
            artist=track.artist,
            cover_uri=track.cover_uri
        )

    def _update_ui(self):
        pos = self.audio_controller.player.position()
        dur = self.audio_controller.player.duration()
        self.controls.update_position(pos, dur)

    def _on_player_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        self.controls.set_playing_state(state == QMediaPlayer.PlayingState)

    def _toggle_login(self):
        if self.auth_status:
            # Выход
            self.auth_status = False
            self.api.clear_tokens()
            self.nav_panel.set_login_status(False)
            self.status_bar.showMessage("Вы вышли из системы", 3000)
        else:
            self._show_login_dialog()

    def _show_login_dialog(self):
        dialog = QDialog(self)
        dialog.setWindowTitle("Вход")
        layout = QFormLayout(dialog)
        edit_login = QLineEdit()
        edit_pass = QLineEdit()
        edit_pass.setEchoMode(QLineEdit.Password)
        layout.addRow("Логин:", edit_login)
        layout.addRow("Пароль:", edit_pass)
        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        buttons.accepted.connect(dialog.accept)
        buttons.rejected.connect(dialog.reject)
        layout.addRow(buttons)

        if dialog.exec() == QDialog.Accepted:
            login = edit_login.text().strip()
            password = edit_pass.text().strip()
            if login and password:
                self.api.login(login, password)

    def _on_login_success(self, access, refresh):
        self.auth_status = True
        self.nav_panel.set_login_status(True)
        self.api.set_tokens(access, refresh)
        QMessageBox.information(self, "Успех", "Вы вошли в систему")

    def _search_server(self, query):
        if not self.auth_status:
            QMessageBox.warning(self, "Требуется вход", "Сначала войдите в аккаунт")
            return
        self.status_bar.showMessage(f"Поиск '{query}'...")
        self.api.search_tracks(query)

    def _on_search_finished(self, tracks: List[Track]):
        self.status_bar.showMessage(f"Найдено треков: {len(tracks)}", 3000)
        if not tracks:
            QMessageBox.information(self, "Поиск", "Ничего не найдено")
            return
        for track in tracks:
            self.track_model.addTrack(track)
        if self.current_playlist is None:
            self.current_playlist = Playlist(name="Результаты поиска", tracks=self.track_model.tracks(),
                                             playlist_type="server")
        else:
            self.current_playlist.tracks = self.track_model.tracks()

    def add_local_files(self):
        files, _ = QFileDialog.getOpenFileNames(
            self, "Выберите аудиофайлы", "",
            "Аудио (*.mp3 *.wav *.ogg *.flac);;Все файлы (*.*)"
        )
        for file_path in files:
            path = Path(file_path)
            track = Track(
                title=path.stem,
                artist="Локальный",
                url=file_path,
                is_local=True
            )
            self.track_model.addTrack(track)
        if self.current_playlist is None:
            self.current_playlist = Playlist(name="Локальные файлы", tracks=self.track_model.tracks())
        else:
            self.current_playlist.tracks = self.track_model.tracks()

    def clear_playlist(self):
        self.track_model.clear()
        self.current_playlist = None
        self.current_track_index = -1

    def save_current_playlist(self):
        if self.track_model.rowCount() == 0:
            QMessageBox.information(self, "Пусто", "Плейлист пуст")
            return
        name, ok = QInputDialog.getText(self, "Сохранить плейлист", "Название:")
        if not ok or not name.strip():
            return
        name = name.strip()
        playlist = Playlist(name=name, tracks=self.track_model.tracks())
        if self.track_model.tracks()[0].is_local:
            playlist.playlist_type = "local"
        else:
            playlist.playlist_type = "server"
        self._save_playlist_to_file(playlist)
        self._load_playlists()

    def _save_playlist_to_file(self, playlist: Playlist):
        file_path = self.playlists_dir / f"{playlist.name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(playlist.to_dict(), f, indent=2)

    def _load_playlists(self):
        self.local_playlists.clear()
        self.server_playlists.clear()
        for file in self.playlists_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                pl = Playlist.from_dict(data)
                if pl.playlist_type == "local":
                    self.local_playlists.append(pl)
                else:
                    self.server_playlists.append(pl)
            except Exception as e:
                print(f"Error loading {file}: {e}")

    def load_playlist_dialog(self):
        if not self.local_playlists:
            QMessageBox.information(self, "Нет плейлистов", "Сохранённых плейлистов нет")
            return
        items = [pl.name for pl in self.local_playlists]
        name, ok = QInputDialog.getItem(self, "Загрузить плейлист", "Выберите:", items, 0, False)
        if ok and name:
            for pl in self.local_playlists:
                if pl.name == name:
                    self._set_current_playlist(pl)
                    break

    def _set_current_playlist(self, playlist: Playlist):
        self.current_playlist = playlist
        self.track_model.clear()
        for track in playlist.tracks:
            self.track_model.addTrack(track)
        self.current_track_index = -1
        self.stacked.setCurrentIndex(0)

    def _play_track_at_index(self, index: int):
        if 0 <= index < self.track_model.rowCount():
            self.current_track_index = index
            track = self.track_model.tracks()[index]
            if not track.is_local:
                stream_url = self.api.get_stream_url(track.server_id)
                track.url = stream_url
            self.audio_controller.play_track(track)

    def _next_track(self):
        if self.track_model.rowCount() == 0:
            return
        self.current_track_index = (self.current_track_index + 1) % self.track_model.rowCount()
        self._play_track_at_index(self.current_track_index)

    def _prev_track(self):
        if self.track_model.rowCount() == 0:
            return
        self.current_track_index = (self.current_track_index - 1) % self.track_model.rowCount()
        self._play_track_at_index(self.current_track_index)