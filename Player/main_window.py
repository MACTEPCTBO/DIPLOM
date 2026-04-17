import json
from pathlib import Path
from typing import List, Optional

from PySide6.QtCore import Qt, QTimer
from PySide6.QtWidgets import (
    QMainWindow, QWidget, QHBoxLayout, QVBoxLayout,
    QFileDialog, QMessageBox, QInputDialog, QDialog,
    QFormLayout, QLineEdit, QDialogButtonBox, QStackedWidget,
    QStatusBar, QLabel, QPushButton, QMenu, QListWidget, QListWidgetItem
)
from PySide6.QtGui import QPalette, QColor

from models import Track, Playlist, TrackListModel, HistoryEntry, HistoryListModel
from api import ServerAPI
from player import AudioController
from widgets import (
    NavigationPanel, SearchBar, PlaybackControls, PlaylistView,
    RadioWidget, HistoryWidget, SimplePlaylistView
)


class MainWindow(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("Audio Player")
        self.resize(1100, 700)
        self._apply_dark_theme()

        self.api = ServerAPI()
        self.audio_controller = AudioController()
        self.track_model = TrackListModel()          # модель для главной страницы
        self.history_model = HistoryListModel()

        self.current_playlist: Optional[Playlist] = None
        self.current_track_index: int = -1
        self.local_playlists: List[Playlist] = []
        self.server_playlists: List[Playlist] = []   # кэш списка плейлистов с сервера
        self.likes_cache_path = Path("likes_cache.json")
        self.playlists_dir = Path("playlists")
        self.playlists_dir.mkdir(exist_ok=True)

        self.auth_status = False
        self.current_track_liked = False
        self.current_track_disliked = False

        self._setup_ui()
        self._connect_signals()
        self._load_local_playlists()
        self.api.load_radio_stations()

        self.update_timer = QTimer()
        self.update_timer.timeout.connect(self._update_ui)
        self.update_timer.start(200)

        self._check_auto_login()

    # ------------------------------------------------------------------
    # Кэширование понравившихся треков
    # ------------------------------------------------------------------
    def _save_likes_cache(self, tracks: List[Track]):
        data = [t.to_dict() for t in tracks]
        with open(self.likes_cache_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def _load_likes_cache(self) -> Optional[List[Track]]:
        if not self.likes_cache_path.exists():
            return None
        try:
            with open(self.likes_cache_path, 'r', encoding='utf-8') as f:
                data = json.load(f)
            return [Track.from_dict(item) for item in data]
        except Exception as e:
            print(f"Failed to load likes cache: {e}")
            return None

    # ------------------------------------------------------------------
    # Инициализация и тема
    # ------------------------------------------------------------------
    def _check_auto_login(self):
        if self.api.access_token:
            self.auth_status = True
            self.nav_panel.set_login_status(True)
            self.status_bar.showMessage("Автоматический вход выполнен", 3000)
            QTimer.singleShot(500, self._load_likes_playlist)
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

    # ------------------------------------------------------------------
    # Построение UI
    # ------------------------------------------------------------------
    def _setup_ui(self):
        central = QWidget()
        self.setCentralWidget(central)
        v_main = QVBoxLayout(central)
        v_main.setContentsMargins(0, 0, 0, 0)
        v_main.setSpacing(0)

        h_content = QHBoxLayout()
        h_content.setSpacing(0)

        self.nav_panel = NavigationPanel()
        h_content.addWidget(self.nav_panel)

        self.stacked = QStackedWidget()
        h_content.addWidget(self.stacked, 1)

        v_main.addLayout(h_content, 1)

        self.controls = PlaybackControls()
        v_main.addWidget(self.controls)

        # ----- Главная страница (индекс 0) -----
        home_widget = QWidget()
        home_layout = QVBoxLayout(home_widget)
        home_layout.setContentsMargins(20, 20, 20, 0)
        home_layout.setSpacing(20)

        search_container = QHBoxLayout()
        search_container.addStretch()
        self.search_bar = SearchBar()
        search_container.addWidget(self.search_bar)
        search_container.addStretch()
        home_layout.addLayout(search_container)

        self.playlist_view = PlaylistView(self.track_model)
        home_layout.addWidget(self.playlist_view, 1)
        self.stacked.addWidget(home_widget)

        # ----- Понравившееся (индекс 1) -----
        likes_widget = QWidget()
        likes_layout = QVBoxLayout(likes_widget)
        likes_layout.setContentsMargins(20, 20, 20, 0)
        likes_layout.setSpacing(10)

        self.likes_model = TrackListModel()
        self.likes_playlist_view = SimplePlaylistView(self.likes_model)
        likes_layout.addWidget(self.likes_playlist_view, 1)

        btn_refresh_likes = QPushButton("🔄 Обновить")
        btn_refresh_likes.clicked.connect(self._load_likes_playlist)
        likes_layout.addWidget(btn_refresh_likes)

        self.stacked.addWidget(likes_widget)

        # ----- История (индекс 2) -----
        self.history_widget = HistoryWidget(self.history_model)
        self.history_widget.track_selected.connect(self._play_track_from_history)
        self.stacked.addWidget(self.history_widget)

        # ----- Серверные плейлисты (индекс 3) -----
        server_pl_widget = QWidget()
        server_pl_layout = QVBoxLayout(server_pl_widget)
        server_pl_layout.setContentsMargins(20, 20, 20, 0)
        server_pl_layout.setSpacing(10)

        title = QLabel("Серверные плейлисты")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        server_pl_layout.addWidget(title)

        self.server_playlist_list = QListWidget()
        self.server_playlist_list.setStyleSheet("""
            QListWidget {
                background-color: #1E1E1E;
                border: none;
                color: white;
                font-size: 14px;
            }
            QListWidget::item {
                padding: 10px;
                border-bottom: 1px solid #333333;
            }
            QListWidget::item:hover {
                background-color: #2A2A2A;
            }
        """)
        self.server_playlist_list.itemDoubleClicked.connect(self._on_server_playlist_selected)
        server_pl_layout.addWidget(self.server_playlist_list)

        btn_refresh_server = QPushButton("🔄 Обновить список")
        btn_refresh_server.clicked.connect(self._load_server_playlists)
        server_pl_layout.addWidget(btn_refresh_server)

        self.stacked.addWidget(server_pl_widget)

        # ----- Радио (индекс 4, создаётся позже) -----
        self.radio_placeholder = QWidget()
        self.stacked.addWidget(self.radio_placeholder)

        self.status_bar = QStatusBar()
        self.setStatusBar(self.status_bar)
        self.status_bar.showMessage("Готов")

    # ------------------------------------------------------------------
    # Подключение сигналов
    # ------------------------------------------------------------------
    def _connect_signals(self):
        self.nav_panel.login_clicked.connect(self._toggle_login)
        self.nav_panel.home_clicked.connect(lambda: self.stacked.setCurrentIndex(0))
        self.nav_panel.likes_clicked.connect(lambda: self.stacked.setCurrentIndex(1))
        self.nav_panel.history_clicked.connect(lambda: self.stacked.setCurrentIndex(2))
        self.nav_panel.playlists_clicked.connect(lambda: self.stacked.setCurrentIndex(3))
        self.nav_panel.radio_clicked.connect(self._show_radio_widget)

        self.search_bar.search_requested.connect(self._search_server)

        self.controls.play_clicked.connect(self.audio_controller.toggle_play_pause)
        self.controls.next_clicked.connect(self._next_track)
        self.controls.prev_clicked.connect(self._prev_track)
        self.controls.volume_changed.connect(self.audio_controller.set_volume)
        self.controls.position_changed.connect(self.audio_controller.set_position)
        self.controls.like_clicked.connect(self._toggle_like)
        self.controls.dislike_clicked.connect(self._toggle_dislike)

        btn_add, btn_clear, btn_save, btn_load = self.playlist_view.get_buttons()
        btn_add.clicked.connect(self.add_local_files)
        btn_clear.clicked.connect(self.clear_playlist)
        btn_save.clicked.connect(self.save_current_playlist)
        btn_load.clicked.connect(self.load_playlist_dialog)
        self.playlist_view.track_selected.connect(self._play_track_at_index)

        self.audio_controller.duration_changed.connect(self.controls.set_duration)
        self.audio_controller.state_changed.connect(self._on_player_state_changed)
        self.audio_controller.error_occurred.connect(lambda msg: QMessageBox.warning(self, "Ошибка", msg))
        self.audio_controller.track_changed.connect(self._on_track_changed)
        self.audio_controller.track_finished.connect(self._on_track_finished)

        self.api.login_success.connect(self._on_login_success)
        self.api.login_failed.connect(lambda msg: QMessageBox.critical(self, "Ошибка входа", msg))
        self.api.search_finished.connect(self._on_search_finished)
        self.api.search_failed.connect(lambda msg: QMessageBox.warning(self, "Поиск не удался", msg))
        self.api.playlist_loaded.connect(self._on_playlist_loaded)
        self.api.playlist_load_failed.connect(lambda msg: QMessageBox.warning(self, "Ошибка плейлиста", msg))
        self.api.like_status_changed.connect(self._on_like_status_changed)
        self.api.token_refreshed.connect(self._on_token_refreshed)

        self.playlist_view.list_view.setContextMenuPolicy(Qt.CustomContextMenu)
        self.playlist_view.list_view.customContextMenuRequested.connect(self._show_track_context_menu)

        self.likes_playlist_view.track_selected.connect(self._play_track_from_likes)

    # ------------------------------------------------------------------
    # Обработчики плеера
    # ------------------------------------------------------------------
    def _on_track_changed(self, track: Track):
        info = (track.title, track.artist, track.cover_uri)
        self.playlist_view.set_current_track_info(*info)
        self.likes_playlist_view.set_current_track_info(*info)
        self.current_track_liked = False
        self.current_track_disliked = False
        self._update_like_buttons_ui()

    def _on_track_finished(self):
        self._next_track()

    def _update_ui(self):
        pos = self.audio_controller.player.position()
        dur = self.audio_controller.player.duration()
        self.controls.update_position(pos, dur)

    def _on_player_state_changed(self, state):
        from PySide6.QtMultimedia import QMediaPlayer
        self.controls.set_playing_state(state == QMediaPlayer.PlayingState)

    # ------------------------------------------------------------------
    # Аутентификация
    # ------------------------------------------------------------------
    def _toggle_login(self):
        if self.auth_status:
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
        self._load_likes_playlist()
        self._load_server_playlists()

    def _on_token_refreshed(self, access, refresh):
        self.status_bar.showMessage("Токен обновлён", 2000)

    # ------------------------------------------------------------------
    # Поиск и плейлисты
    # ------------------------------------------------------------------
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

        if self.track_model.rowCount() > 0:
            for track in self.track_model.tracks():
                self.history_model.add_entry(HistoryEntry(track=track))

        self.track_model.clear()
        for track in tracks:
            self.track_model.addTrack(track)

        self.current_playlist = Playlist(name="Результаты поиска", tracks=self.track_model.tracks(),
                                         playlist_type="server")
        self.current_track_index = -1

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
        if self.track_model.rowCount() > 0:
            for track in self.track_model.tracks():
                self.history_model.add_entry(HistoryEntry(track=track))
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
        self._load_local_playlists()

    def _save_playlist_to_file(self, playlist: Playlist):
        file_path = self.playlists_dir / f"{playlist.name}.json"
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(playlist.to_dict(), f, indent=2)

    def _load_local_playlists(self):
        self.local_playlists.clear()
        for file in self.playlists_dir.glob("*.json"):
            try:
                with open(file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                pl = Playlist.from_dict(data)
                self.local_playlists.append(pl)
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
        if self.track_model.rowCount() > 0:
            for track in self.track_model.tracks():
                self.history_model.add_entry(HistoryEntry(track=track))

        self.current_playlist = playlist
        self.track_model.clear()
        for track in playlist.tracks:
            self.track_model.addTrack(track)
        self.current_track_index = -1
        self.stacked.setCurrentIndex(0)

    def _load_server_playlists(self):
        if not self.auth_status:
            return
        # Заглушка – замените на реальный вызов API
        self.server_playlists = [
            Playlist(id=1, name="Chill Mix", tracks=[], playlist_type="server"),
            Playlist(id=2, name="Workout", tracks=[], playlist_type="server"),
        ]
        self._update_server_playlist_list()

    def _update_server_playlist_list(self):
        self.server_playlist_list.clear()
        for pl in self.server_playlists:
            item = QListWidgetItem(f"{pl.name} ({pl.count} треков)")
            item.setData(Qt.UserRole, pl)
            self.server_playlist_list.addItem(item)

    def _on_server_playlist_selected(self, item: QListWidgetItem):
        playlist = item.data(Qt.UserRole)
        if not playlist:
            return
        self.status_bar.showMessage(f"Загрузка плейлиста '{playlist.name}'...")
        self.api.get_playlist_by_name(str(playlist.id))

    def _on_playlist_loaded(self, playlist: Playlist):
        self.status_bar.showMessage(f"Плейлист '{playlist.name}' загружен", 3000)
        if playlist.name == "Понравившиеся" or playlist.id == -1:
            self.likes_model.clear()
            for track in playlist.tracks:
                self.likes_model.addTrack(track)
            self._save_likes_cache(playlist.tracks)
        else:
            self._set_current_playlist(playlist)

    # ------------------------------------------------------------------
    # Воспроизведение и навигация по трекам
    # ------------------------------------------------------------------
    def _play_track_at_index(self, index: int):
        if 0 <= index < self.track_model.rowCount():
            self.current_track_index = index
            track = self.track_model.tracks()[index]
            self._prepare_and_play_track(track)

    def _play_track_from_likes(self, index: int):
        if 0 <= index < self.likes_model.rowCount():
            track = self.likes_model.tracks()[index]
            self._prepare_and_play_track(track)

    def _play_track_from_history(self, track: Track):
        if track not in self.track_model.tracks():
            self.track_model.addTrack(track)
        self.current_track_index = self.track_model.tracks().index(track)
        self._prepare_and_play_track(track)

    def _prepare_and_play_track(self, track: Track):
        if not track.is_local and track.server_id:
            track.url = self.api.get_stream_url(track.server_id)
        self.audio_controller.play_track(track)
        self.history_model.add_entry(HistoryEntry(track=track))
        self.playlist_view.set_current_track_info(track.title, track.artist, track.cover_uri)
        self.likes_playlist_view.set_current_track_info(track.title, track.artist, track.cover_uri)

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

    # ------------------------------------------------------------------
    # Лайки / дизлайки
    # ------------------------------------------------------------------
    def _toggle_like(self):
        if not self.audio_controller.current_track or self.audio_controller.current_track.is_local:
            return
        track_id = self.audio_controller.current_track.id
        new_state = not self.current_track_liked
        self.api.like_track(track_id, like=new_state)
        self.current_track_liked = new_state
        if new_state:
            self.current_track_disliked = False
        self._update_like_buttons_ui()

    def _toggle_dislike(self):
        if not self.audio_controller.current_track or self.audio_controller.current_track.is_local:
            return
        track_id = self.audio_controller.current_track.id
        new_state = not self.current_track_disliked
        self.api.dislike_track(track_id, dislike=new_state)
        self.current_track_disliked = new_state
        if new_state:
            self.current_track_liked = False
        self._update_like_buttons_ui()

    def _update_like_buttons_ui(self):
        self.controls.set_like_state(self.current_track_liked)
        self.controls.set_dislike_state(self.current_track_disliked)

    def _load_likes_playlist(self):
        if not self.auth_status:
            return
        cached_tracks = self._load_likes_cache()
        if cached_tracks:
            self.likes_model.clear()
            for track in cached_tracks:
                self.likes_model.addTrack(track)
            self.status_bar.showMessage("Понравившиеся треки загружены из кэша", 2000)
        self.status_bar.showMessage("Обновление понравившихся треков с сервера...")
        self.api.get_likes_playlist()

    def _show_track_context_menu(self, pos):
        index = self.playlist_view.list_view.indexAt(pos)
        if not index.isValid():
            return
        track = index.data(Qt.UserRole)
        if not track or track.is_local:
            return

        menu = QMenu()
        like_action = menu.addAction("❤️ Нравится")
        dislike_action = menu.addAction("👎 Не нравится")
        action = menu.exec(self.playlist_view.list_view.viewport().mapToGlobal(pos))
        if action == like_action:
            self.api.like_track(track.id, like=True)
        elif action == dislike_action:
            self.api.dislike_track(track.id, dislike=True)

    def _on_like_status_changed(self, success: bool):
        if success:
            self.status_bar.showMessage("Оценка обновлена", 2000)
            self._load_likes_playlist()
        else:
            self.current_track_liked = not self.current_track_liked
            self._update_like_buttons_ui()
            QMessageBox.warning(self, "Ошибка", "Не удалось изменить оценку")

    def _on_like_current_track(self):
        self._toggle_like()

    def _on_dislike_current_track(self):
        self._toggle_dislike()

    # ------------------------------------------------------------------
    # Радио
    # ------------------------------------------------------------------
    def _show_radio_widget(self):
        if not hasattr(self, 'radio_widget'):
            self.radio_widget = RadioWidget()
            self.radio_widget.station_selected.connect(self._on_radio_station_selected)
            self.stacked.removeWidget(self.radio_placeholder)
            self.stacked.insertWidget(4, self.radio_widget)
        self.stacked.setCurrentIndex(4)

    def _on_radio_stations_loaded(self, stations: list):
        if hasattr(self, 'radio_widget'):
            self.radio_widget.load_stations(stations)

    def _on_radio_station_selected(self, station: dict):
        QMessageBox.information(self, "Радио", f"Выбрана станция: {station.get('name')}\n(функционал в разработке)")