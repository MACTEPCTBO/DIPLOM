from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QTreeWidget, QTreeWidgetItem, QHeaderView, QMenu, QAbstractItemView, QLabel, QStyle
)
from PySide6.QtCore import Qt, QUrl, Signal, QSize
from PySide6.QtGui import QIcon, QPixmap
from PySide6.QtMultimedia import QMediaPlayer, QMediaMetaData
import json
import os
from mutagen import File as MutagenFile  # требуется pip install mutagen

class PlaylistView(QWidget):
    """Визуализация плейлиста в виде таблицы с колонками: Обложка, Название, Исполнитель, Длительность."""
    def __init__(self, playlist_manager, player, parent=None):
        super().__init__(parent)
        self.playlist = playlist_manager
        self.player = player

        layout = QVBoxLayout()
        layout.setContentsMargins(0, 0, 0, 0)

        self.header = QLabel("<b>Текущий плейлист</b>")
        layout.addWidget(self.header)

        self.tree = QTreeWidget()
        self.tree.setColumnCount(4)
        self.tree.setHeaderLabels(["", "Название", "Исполнитель", "Длительность"])
        self.tree.setSelectionMode(QAbstractItemView.ExtendedSelection)
        self.tree.setAlternatingRowColors(True)
        self.tree.setIconSize(QSize(40, 40))
        self.tree.header().setSectionResizeMode(1, QHeaderView.Stretch)
        self.tree.setColumnWidth(0, 50)
        self.tree.itemDoubleClicked.connect(self._play_selected)
        self.tree.setContextMenuPolicy(Qt.CustomContextMenu)
        self.tree.customContextMenuRequested.connect(self._show_context_menu)

        layout.addWidget(self.tree)
        self.setLayout(layout)

        self.playlist.playlistChanged.connect(self.update_display)
        self.playlist.currentIndexChanged.connect(self._highlight_current)

        self.default_icon = QIcon.fromTheme("audio-x-generic")
        if self.default_icon.isNull():
            self.default_icon = self.style().standardIcon(QStyle.StandardPixmap.SP_FileIcon)

    def update_display(self):
        self.tree.clear()
        for i in range(self.playlist.mediaCount()):
            url = self.playlist.media(i)
            file_path = url.toLocalFile() if url.isLocalFile() else url.toString()
            # Извлекаем метаданные
            title, artist, duration_str, cover = self._extract_metadata(file_path)
            item = QTreeWidgetItem()
            item.setData(0, Qt.UserRole, url)
            # Колонка 0: обложка
            if cover:
                pixmap = QPixmap()
                pixmap.loadFromData(cover)
                icon = QIcon(pixmap.scaled(40, 40, Qt.KeepAspectRatio, Qt.SmoothTransformation))
            else:
                icon = self.default_icon
            item.setIcon(0, icon)
            # Колонка 1: название
            item.setText(1, title)
            # Колонка 2: исполнитель
            item.setText(2, artist)
            # Колонка 3: длительность
            item.setText(3, duration_str)
            self.tree.addTopLevelItem(item)
        self._highlight_current(self.playlist.currentIndex())

    def _extract_metadata(self, file_path):
        title = os.path.basename(file_path)
        artist = ""
        duration_str = ""
        cover = None
        if os.path.exists(file_path):
            try:
                audio = MutagenFile(file_path)
                if audio is not None:
                    if 'title' in audio and audio['title']:
                        title = str(audio['title'][0])
                    if 'artist' in audio and audio['artist']:
                        artist = str(audio['artist'][0])
                    if audio.info.length:
                        duration_str = self._format_duration(audio.info.length)
                    # Извлечение обложки
                    if hasattr(audio, 'pictures'):
                        for pic in audio.pictures:
                            cover = pic.data
                            break
                    elif 'APIC:' in audio:  # для MP3
                        cover = audio['APIC:'].data
            except Exception:
                pass
        # Для серверных URL длительность получим позже через плеер
        return title, artist, duration_str, cover

    def _format_duration(self, seconds):
        m, s = divmod(int(seconds), 60)
        return f"{m}:{s:02d}"

    def _play_selected(self, item, column):
        index = self.tree.indexOfTopLevelItem(item)
        self.player.play_playlist_at(index)

    def _highlight_current(self, index):
        for i in range(self.tree.topLevelItemCount()):
            item = self.tree.topLevelItem(i)
            if i == index:
                font = item.font(1)
                font.setBold(True)
                for col in range(4):
                    item.setFont(col, font)
                self.tree.setCurrentItem(item)
            else:
                font = item.font(1)
                font.setBold(False)
                for col in range(4):
                    item.setFont(col, font)

    def _show_context_menu(self, pos):
        item = self.tree.itemAt(pos)
        if not item:
            return
        menu = QMenu()
        remove_action = menu.addAction("Удалить из плейлиста")
        action = menu.exec(self.tree.mapToGlobal(pos))
        if action == remove_action:
            self._remove_selected()

    def _remove_selected(self):
        for item in self.tree.selectedItems():
            row = self.tree.indexOfTopLevelItem(item)
            self.playlist.removeMedia(row)
        # update_display будет вызван через сигнал playlistChanged

    def save_playlist(self, file_path):
        data = self.playlist.to_list()
        with open(file_path, 'w', encoding='utf-8') as f:
            json.dump(data, f, indent=2)

    def load_playlist(self, file_path):
        with open(file_path, 'r', encoding='utf-8') as f:
            urls = json.load(f)
        self.playlist.clear()
        for url_str in urls:
            self.playlist.addMedia(QUrl(url_str))