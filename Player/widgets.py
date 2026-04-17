from PySide6.QtCore import Qt, Signal, QUrl, QRectF, QAbstractListModel
from PySide6.QtGui import QPalette, QColor, QFont, QIcon, QPixmap, QPainter
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QHBoxLayout, QPushButton, QLabel,
    QSlider, QListView, QLineEdit, QFrame, QListWidget, QListWidgetItem
)
from PySide6.QtNetwork import QNetworkAccessManager, QNetworkRequest, QNetworkReply

from PySide6.QtCore import QSize, QModelIndex, QRect, Qt
from PySide6.QtGui import QPainter, QPixmap, QFont, QColor, QPen
from PySide6.QtWidgets import QStyledItemDelegate, QStyle

from models import TrackListModel, HistoryListModel, Track


class CoverLabel(QLabel):
    """Виджет для отображения обложки трека с асинхронной загрузкой"""
    def __init__(self, parent=None, size: int = 120):
        super().__init__(parent)
        self.setFixedSize(size, size)
        self.setStyleSheet("""
            QLabel {
                background-color: #282828;
                border-radius: 8px;
            }
        """)
        self.setScaledContents(True)
        self.setAlignment(Qt.AlignCenter)
        self._default_pixmap = self._create_default_pixmap(size)
        self.setPixmap(self._default_pixmap)
        self._nam = QNetworkAccessManager()
        self._nam.finished.connect(self._on_reply)
        self._cache = {}
        self._current_url = ""

    def _create_default_pixmap(self, size: int) -> QPixmap:
        pixmap = QPixmap(size, size)
        pixmap.fill(QColor("#404040"))
        painter = QPainter(pixmap)
        painter.setPen(QColor("#AAAAAA"))
        font = painter.font()
        font.setPointSize(size // 3)
        painter.setFont(font)
        painter.drawText(QRectF(0, 0, size, size), Qt.AlignCenter, "♪")
        painter.end()
        return pixmap

    def set_cover_uri(self, uri: str):
        if not uri:
            self.setPixmap(self._default_pixmap)
            self._current_url = ""
            return

        if uri in self._cache:
            self.setPixmap(self._cache[uri])
            self._current_url = uri
            return

        self._current_url = uri
        self.setPixmap(self._default_pixmap)

        if uri.startswith("file://") or (not uri.startswith("http")):
            local_path = uri.replace("file://", "")
            pixmap = QPixmap(local_path)
            if not pixmap.isNull():
                scaled = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._cache[uri] = scaled
                if self._current_url == uri:
                    self.setPixmap(scaled)
            return

        req = QNetworkRequest(QUrl(uri))
        self._nam.get(req)

    def _on_reply(self, reply: QNetworkReply):
        if reply.error() != QNetworkReply.NoError:
            reply.deleteLater()
            return

        data = reply.readAll()
        pixmap = QPixmap()
        pixmap.loadFromData(data)

        if not pixmap.isNull():
            scaled = pixmap.scaled(self.width(), self.height(), Qt.KeepAspectRatio, Qt.SmoothTransformation)
            url = reply.url().toString()
            self._cache[url] = scaled
            if self._current_url == url:
                self.setPixmap(scaled)

        reply.deleteLater()


class NavigationPanel(QWidget):
    login_clicked = Signal()
    home_clicked = Signal()
    likes_clicked = Signal()
    history_clicked = Signal()
    playlists_clicked = Signal()
    radio_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedWidth(220)
        self.setStyleSheet("""
            QWidget {
                background-color: #1E1E1E;
                color: #FFFFFF;
            }
            QPushButton {
                text-align: left;
                padding: 10px 20px;
                border: none;
                border-radius: 8px;
                font-size: 14px;
                font-weight: 500;
                background-color: transparent;
            }
            QPushButton:hover {
                background-color: #333333;
            }
            QPushButton:pressed {
                background-color: #444444;
            }
        """)
        layout = QVBoxLayout(self)
        layout.setContentsMargins(10, 20, 10, 20)
        layout.setSpacing(5)

        title = QLabel("Audio Player")
        title.setStyleSheet("font-size: 20px; font-weight: bold; margin-bottom: 20px; color: #1DB954;")
        title.setAlignment(Qt.AlignCenter)
        layout.addWidget(title)

        self.btn_home = QPushButton("🏠 Главная")
        self.btn_home.clicked.connect(self.home_clicked)
        layout.addWidget(self.btn_home)

        self.btn_likes = QPushButton("❤️ Понравившееся")
        self.btn_likes.clicked.connect(self.likes_clicked)
        layout.addWidget(self.btn_likes)

        self.btn_history = QPushButton("🕒 История")
        self.btn_history.clicked.connect(self.history_clicked)
        layout.addWidget(self.btn_history)

        self.btn_playlists = QPushButton("📋 Плейлисты")
        self.btn_playlists.clicked.connect(self.playlists_clicked)
        layout.addWidget(self.btn_playlists)

        self.btn_radio = QPushButton("📻 Радио")
        self.btn_radio.clicked.connect(self.radio_clicked)
        layout.addWidget(self.btn_radio)

        layout.addStretch()

        self.btn_login = QPushButton("👤 Войти")
        self.btn_login.clicked.connect(self.login_clicked)
        layout.addWidget(self.btn_login)

        self.login_status = QLabel("Не авторизован")
        self.login_status.setStyleSheet("font-size: 12px; color: #AAAAAA; padding-left: 20px;")
        layout.addWidget(self.login_status)

    def set_login_status(self, logged_in: bool):
        if logged_in:
            self.btn_login.setText("👤 Выйти")
            self.login_status.setText("Авторизован")
        else:
            self.btn_login.setText("👤 Войти")
            self.login_status.setText("Не авторизован")


class SearchBar(QWidget):
    search_requested = Signal(str)

    def __init__(self):
        super().__init__()
        layout = QHBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        self.edit = QLineEdit()
        self.edit.setPlaceholderText("Поиск треков на сервере...")
        self.edit.setStyleSheet("""
            QLineEdit {
                background-color: #333333;
                border: 1px solid #555555;
                border-radius: 20px;
                padding: 10px 20px;
                color: white;
                font-size: 14px;
            }
            QLineEdit:focus {
                border-color: #1DB954;
            }
        """)
        self.edit.returnPressed.connect(self._on_search)
        layout.addWidget(self.edit)

        self.btn = QPushButton("🔍")
        self.btn.setFixedSize(40, 40)
        self.btn.setStyleSheet("""
            QPushButton {
                background-color: #1DB954;
                border-radius: 20px;
                color: white;
                font-size: 18px;
                border: none;
            }
            QPushButton:hover {
                background-color: #1ED760;
            }
        """)
        self.btn.clicked.connect(self._on_search)
        layout.addWidget(self.btn)

    def _on_search(self):
        text = self.edit.text().strip()
        if text:
            self.search_requested.emit(text)


class PlaybackControls(QWidget):
    play_clicked = Signal()
    next_clicked = Signal()
    prev_clicked = Signal()
    volume_changed = Signal(int)
    position_changed = Signal(int)
    like_clicked = Signal()
    dislike_clicked = Signal()

    def __init__(self):
        super().__init__()
        self.setFixedHeight(90)
        self.setStyleSheet("""
            QWidget {
                background-color: #282828;
                color: white;
            }
            QPushButton {
                background-color: transparent;
                border: none;
                font-size: 22px;
                color: #AAAAAA;
                padding: 5px;
            }
            QPushButton:hover {
                color: white;
            }
            QSlider::groove:horizontal {
                height: 6px;
                background: #404040;
                border-radius: 3px;
            }
            QSlider::handle:horizontal {
                background: #1DB954;
                width: 14px;
                height: 14px;
                margin: -4px 0;
                border-radius: 7px;
            }
            QSlider::handle:horizontal:hover {
                background: #1ED760;
            }
            QSlider::sub-page:horizontal {
                background: #1DB954;
                border-radius: 3px;
            }
        """)

        main_layout = QVBoxLayout(self)
        main_layout.setContentsMargins(20, 10, 20, 10)

        progress_layout = QHBoxLayout()
        self.current_time = QLabel("0:00")
        self.current_time.setStyleSheet("font-size: 12px; color: #AAAAAA;")
        self.total_time = QLabel("0:00")
        self.total_time.setStyleSheet("font-size: 12px; color: #AAAAAA;")

        self.progress_slider = QSlider(Qt.Horizontal)
        self.progress_slider.setRange(0, 0)
        self.progress_slider.sliderMoved.connect(self.position_changed)

        progress_layout.addWidget(self.current_time)
        progress_layout.addWidget(self.progress_slider)
        progress_layout.addWidget(self.total_time)
        main_layout.addLayout(progress_layout)

        controls_layout = QHBoxLayout()
        controls_layout.addStretch()

        self.btn_prev = QPushButton("⏮")
        self.btn_prev.clicked.connect(self.prev_clicked)
        controls_layout.addWidget(self.btn_prev)

        self.btn_play = QPushButton("▶")
        self.btn_play.clicked.connect(self.play_clicked)
        self.btn_play.setStyleSheet("font-size: 28px;")
        controls_layout.addWidget(self.btn_play)

        self.btn_next = QPushButton("⏭")
        self.btn_next.clicked.connect(self.next_clicked)
        controls_layout.addWidget(self.btn_next)

        self.btn_like = QPushButton("❤️")
        self.btn_like.clicked.connect(self.like_clicked)
        controls_layout.addWidget(self.btn_like)

        self.btn_dislike = QPushButton("👎")
        self.btn_dislike.clicked.connect(self.dislike_clicked)
        controls_layout.addWidget(self.btn_dislike)

        controls_layout.addStretch()

        volume_label = QLabel("🔊")
        volume_label.setStyleSheet("font-size: 16px;")
        controls_layout.addWidget(volume_label)

        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(70)
        self.volume_slider.setFixedWidth(100)
        self.volume_slider.valueChanged.connect(self.volume_changed)
        controls_layout.addWidget(self.volume_slider)

        main_layout.addLayout(controls_layout)

        self.like_active = False
        self.dislike_active = False

    def set_playing_state(self, playing: bool):
        self.btn_play.setText("⏸" if playing else "▶")

    def update_position(self, pos: int, duration: int):
        if not self.progress_slider.isSliderDown():
            self.progress_slider.setValue(pos)
        self.current_time.setText(self._format_time(pos))
        self.total_time.setText(self._format_time(duration))

    def set_duration(self, duration: int):
        self.progress_slider.setRange(0, duration)
        self.total_time.setText(self._format_time(duration))

    def _format_time(self, ms: int) -> str:
        if ms <= 0:
            return "0:00"
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m}:{s:02d}"

    def set_like_state(self, active: bool):
        self.like_active = active
        color = "#1DB954" if active else "#AAAAAA"
        self.btn_like.setStyleSheet(f"font-size: 22px; color: {color}; background: transparent; border: none;")

    def set_dislike_state(self, active: bool):
        self.dislike_active = active
        color = "#E62E2E" if active else "#AAAAAA"
        self.btn_dislike.setStyleSheet(f"font-size: 22px; color: {color}; background: transparent; border: none;")


class PlaylistView(QWidget):
    track_selected = Signal(int)

    def __init__(self, model):
        super().__init__()
        self.model = model
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)

        self.cover_label = CoverLabel(size=100)
        top_layout.addWidget(self.cover_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        self.track_title_label = QLabel("Ничего не играет")
        self.track_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.track_artist_label = QLabel("—")
        self.track_artist_label.setStyleSheet("font-size: 14px; color: #AAAAAA;")
        info_layout.addWidget(self.track_title_label)
        info_layout.addWidget(self.track_artist_label)
        info_layout.addStretch()
        top_layout.addLayout(info_layout)
        top_layout.addStretch()

        layout.addWidget(top_widget)

        title = QLabel("Текущий плейлист")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(title)

        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.delegate = TrackItemDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setStyleSheet("""
            QListView {
                background-color: #121212;
                border: none;
                color: white;
                font-size: 14px;
                outline: none;
            }
            QListView::item {
                border-bottom: 1px solid #333333;
            }
            QListView::item:hover {
                background-color: #2A2A2A;
            }
        """)
        self.list_view.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_view, 1)

        btn_layout = QHBoxLayout()
        self.btn_add_local = QPushButton("➕ Добавить локальные")
        self.btn_clear = QPushButton("🗑 Очистить")
        self.btn_save = QPushButton("💾 Сохранить")
        self.btn_load = QPushButton("📂 Загрузить")
        for btn in (self.btn_add_local, self.btn_clear, self.btn_save, self.btn_load):
            btn.setStyleSheet("""
                QPushButton {
                    background-color: #333333;
                    border: none;
                    border-radius: 5px;
                    padding: 8px 12px;
                }
                QPushButton:hover {
                    background-color: #444444;
                }
            """)
            btn_layout.addWidget(btn)
        layout.addLayout(btn_layout)

    def _on_double_click(self, index):
        if index.isValid():
            self.track_selected.emit(index.row())

    def set_current_track_info(self, title: str, artist: str, cover_uri: str = ""):
        self.track_title_label.setText(title if title else "Неизвестный трек")
        self.track_artist_label.setText(artist if artist else "Неизвестный исполнитель")
        self.cover_label.set_cover_uri(cover_uri)

    def get_buttons(self):
        return self.btn_add_local, self.btn_clear, self.btn_save, self.btn_load


class SimplePlaylistView(QWidget):
    track_selected = Signal(int)

    def __init__(self, model):
        super().__init__()
        self.model = model
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        top_widget = QWidget()
        top_layout = QHBoxLayout(top_widget)
        top_layout.setContentsMargins(0, 0, 0, 0)
        top_layout.setSpacing(15)

        self.cover_label = CoverLabel(size=100)
        top_layout.addWidget(self.cover_label)

        info_layout = QVBoxLayout()
        info_layout.setSpacing(5)
        self.track_title_label = QLabel("Ничего не играет")
        self.track_title_label.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        self.track_artist_label = QLabel("—")
        self.track_artist_label.setStyleSheet("font-size: 14px; color: #AAAAAA;")
        info_layout.addWidget(self.track_title_label)
        info_layout.addWidget(self.track_artist_label)
        info_layout.addStretch()
        top_layout.addLayout(info_layout)
        top_layout.addStretch()

        layout.addWidget(top_widget)

        title = QLabel("Понравившиеся треки")
        title.setStyleSheet("font-size: 16px; font-weight: bold; margin-top: 10px;")
        layout.addWidget(title)

        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.delegate = TrackItemDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.setStyleSheet("""
            QListView {
                background-color: #121212;
                border: none;
                color: white;
                font-size: 14px;
                outline: none;
            }
            QListView::item {
                border-bottom: 1px solid #333333;
            }
            QListView::item:hover {
                background-color: #2A2A2A;
            }
        """)
        self.list_view.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_view, 1)

    def _on_double_click(self, index):
        if index.isValid():
            self.track_selected.emit(index.row())

    def set_current_track_info(self, title: str, artist: str, cover_uri: str = ""):
        self.track_title_label.setText(title if title else "Неизвестный трек")
        self.track_artist_label.setText(artist if artist else "Неизвестный исполнитель")
        self.cover_label.set_cover_uri(cover_uri)


class TrackItemDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager()
        self._nam.finished.connect(self._on_pixmap_loaded)
        self._cache = {}
        self._pending = {}

    def paint(self, painter: QPainter, option, index: QModelIndex):
        if not index.isValid():
            return

        painter.save()

        if option.state & QStyle.State_Selected:
            painter.fillRect(option.rect, option.palette.highlight())
        else:
            painter.fillRect(option.rect, QColor("#121212") if index.row() % 2 == 0 else QColor("#1A1A1A"))

        track = index.data(Qt.UserRole)
        cover_uri = index.data(TrackListModel.CoverRole)

        rect = option.rect
        cover_size = 40
        margin = 8
        cover_rect = QRect(rect.left() + margin, rect.top() + (rect.height() - cover_size) // 2,
                           cover_size, cover_size)

        if cover_uri and cover_uri in self._cache:
            pixmap = self._cache[cover_uri]
            painter.drawPixmap(cover_rect, pixmap)
        else:
            painter.setBrush(QColor("#404040"))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(cover_rect, 4, 4)
            painter.setPen(QColor("#AAAAAA"))
            font = painter.font()
            font.setPointSize(16)
            painter.setFont(font)
            painter.drawText(cover_rect, Qt.AlignCenter, "♪")

            if cover_uri and cover_uri not in self._pending:
                self._pending[cover_uri] = []
                req = QNetworkRequest(QUrl(cover_uri))
                self._nam.get(req)
            if cover_uri:
                self._pending[cover_uri].append((index, option.widget))

        text_rect = QRect(cover_rect.right() + margin, rect.top(),
                          rect.width() - cover_rect.width() - 3 * margin, rect.height())
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPointSize(11)
        painter.setFont(font)
        text = track.display_text() if track else "Unknown"
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, text)

        painter.restore()

    def sizeHint(self, option, index: QModelIndex):
        return QSize(option.rect.width(), 50)

    def _on_pixmap_loaded(self, reply: QNetworkReply):
        url = reply.url().toString()
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._cache[url] = scaled
                if url in self._pending:
                    for index, widget in self._pending[url]:
                        if widget:
                            widget.update(index)
                    del self._pending[url]
        reply.deleteLater()


class RadioStationDelegate(QStyledItemDelegate):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._nam = QNetworkAccessManager()
        self._nam.finished.connect(self._on_pixmap_loaded)
        self._cache = {}
        self._pending = {}

    def paint(self, painter: QPainter, option, index: QModelIndex):
        if not index.isValid():
            return

        painter.save()
        rect = option.rect

        if option.state & QStyle.State_Selected:
            painter.fillRect(rect, QColor("#333333"))
        elif option.state & QStyle.State_MouseOver:
            painter.fillRect(rect, QColor("#2A2A2A"))
        else:
            painter.fillRect(rect, QColor("#1E1E1E"))

        station = index.data(Qt.UserRole)
        if not station:
            painter.restore()
            return

        icon_size = 48
        margin = 10
        icon_rect = QRect(rect.left() + margin, rect.top() + (rect.height() - icon_size) // 2,
                          icon_size, icon_size)

        icon_url = station.get("icon", {}).get("image_url", "")
        if icon_url and icon_url in self._cache:
            pixmap = self._cache[icon_url]
            painter.drawPixmap(icon_rect, pixmap)
        else:
            bg_color = station.get("icon", {}).get("background_color", "#404040")
            painter.setBrush(QColor(bg_color))
            painter.setPen(Qt.NoPen)
            painter.drawRoundedRect(icon_rect, 8, 8)
            painter.setPen(QColor("white"))
            font = painter.font()
            font.setPointSize(18)
            painter.setFont(font)
            painter.drawText(icon_rect, Qt.AlignCenter, "♪")

            if icon_url and icon_url not in self._pending:
                self._pending[icon_url] = []
                req = QNetworkRequest(QUrl(icon_url))
                self._nam.get(req)
            if icon_url:
                self._pending[icon_url].append((index, option.widget))

        text_rect = QRect(icon_rect.right() + margin, rect.top(),
                          rect.width() - icon_rect.width() - 3 * margin, rect.height())
        painter.setPen(QColor("white"))
        font = painter.font()
        font.setPointSize(12)
        font.setBold(True)
        painter.setFont(font)
        painter.drawText(text_rect, Qt.AlignLeft | Qt.AlignVCenter, station.get("name", ""))

        painter.restore()

    def sizeHint(self, option, index: QModelIndex):
        return QSize(option.rect.width(), 70)

    def _on_pixmap_loaded(self, reply: QNetworkReply):
        url = reply.url().toString()
        if reply.error() == QNetworkReply.NoError:
            data = reply.readAll()
            pixmap = QPixmap()
            pixmap.loadFromData(data)
            if not pixmap.isNull():
                scaled = pixmap.scaled(48, 48, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                self._cache[url] = scaled
                if url in self._pending:
                    for index, widget in self._pending[url]:
                        if widget:
                            widget.update(index)
                    del self._pending[url]
        reply.deleteLater()


class RadioListModel(QAbstractListModel):
    def __init__(self, stations=None):
        super().__init__()
        self._stations = stations or []

    def rowCount(self, parent=QModelIndex()):
        return len(self._stations)

    def data(self, index, role=Qt.DisplayRole):
        if not index.isValid() or index.row() >= len(self._stations):
            return None
        station = self._stations[index.row()]
        if role == Qt.DisplayRole:
            return station.get("name", "")
        elif role == Qt.UserRole:
            return station
        return None


class RadioWidget(QWidget):
    station_selected = Signal(dict)

    def __init__(self):
        super().__init__()
        self.setup_ui()

    def setup_ui(self):
        layout = QVBoxLayout(self)
        layout.setContentsMargins(0, 0, 0, 0)
        layout.setSpacing(10)

        title = QLabel("Радиостанции")
        title.setStyleSheet("font-size: 20px; font-weight: bold; color: white; margin: 10px;")
        layout.addWidget(title)

        self.list_view = QListView()
        self.list_view.setStyleSheet("""
            QListView {
                background-color: #1E1E1E;
                border: none;
                outline: none;
            }
            QListView::item {
                border-bottom: 1px solid #333333;
            }
        """)
        self.model = RadioListModel()
        self.list_view.setModel(self.model)
        self.delegate = RadioStationDelegate(self.list_view)
        self.list_view.setItemDelegate(self.delegate)
        self.list_view.clicked.connect(self._on_station_clicked)
        layout.addWidget(self.list_view)

    def load_stations(self, stations):
        self.model._stations = stations
        self.model.layoutChanged.emit()

    def _on_station_clicked(self, index):
        station = index.data(Qt.UserRole)
        if station:
            self.station_selected.emit(station)


class HistoryWidget(QWidget):
    track_selected = Signal(Track)

    def __init__(self, model: HistoryListModel):
        super().__init__()
        self.model = model
        layout = QVBoxLayout(self)
        layout.setContentsMargins(20, 20, 20, 0)
        layout.setSpacing(10)

        title = QLabel("История прослушивания")
        title.setStyleSheet("font-size: 18px; font-weight: bold; color: white;")
        layout.addWidget(title)

        self.list_view = QListView()
        self.list_view.setModel(self.model)
        self.list_view.setStyleSheet("""
            QListView {
                background-color: #1E1E1E;
                border: none;
                color: #AAAAAA;
                font-size: 13px;
                outline: none;
            }
            QListView::item {
                border-bottom: 1px solid #333333;
                padding: 5px;
            }
            QListView::item:hover {
                background-color: #2A2A2A;
            }
        """)
        self.list_view.doubleClicked.connect(self._on_double_click)
        layout.addWidget(self.list_view, 1)

        btn_clear = QPushButton("Очистить историю")
        btn_clear.setStyleSheet("""
            QPushButton {
                background-color: #333333;
                border: none;
                border-radius: 5px;
                padding: 8px 12px;
            }
            QPushButton:hover {
                background-color: #444444;
            }
        """)
        btn_clear.clicked.connect(self.model.clear)
        layout.addWidget(btn_clear)

    def _on_double_click(self, index):
        if index.isValid():
            track = index.data(Qt.UserRole)
            if track:
                self.track_selected.emit(track)