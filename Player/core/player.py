from PySide6.QtCore import QObject, Signal, QUrl
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput, QMediaMetaData

class PlaylistManager(QObject):
    """Управляет списком треков и переключением."""
    currentIndexChanged = Signal(int)
    playlistChanged = Signal()

    def __init__(self, parent=None):
        super().__init__(parent)
        self._items = []          # список QUrl
        self._current_index = -1

    def addMedia(self, url: QUrl):
        self._items.append(url)
        self.playlistChanged.emit()

    def addMedias(self, urls):
        self._items.extend(urls)
        self.playlistChanged.emit()

    def removeMedia(self, index):
        if 0 <= index < len(self._items):
            del self._items[index]
            if self._current_index >= len(self._items):
                self._current_index = len(self._items) - 1
            self.playlistChanged.emit()

    def clear(self):
        self._items.clear()
        self._current_index = -1
        self.playlistChanged.emit()

    def mediaCount(self):
        return len(self._items)

    def media(self, index):
        if 0 <= index < len(self._items):
            return self._items[index]
        return QUrl()

    def currentIndex(self):
        return self._current_index

    def setCurrentIndex(self, index):
        if 0 <= index < len(self._items):
            self._current_index = index
            self.currentIndexChanged.emit(index)

    def currentMedia(self):
        return self.media(self._current_index)

    def next(self):
        if self._current_index + 1 < len(self._items):
            self._current_index += 1
            self.currentIndexChanged.emit(self._current_index)
            return True
        return False

    def previous(self):
        if self._current_index > 0:
            self._current_index -= 1
            self.currentIndexChanged.emit(self._current_index)
            return True
        return False

    def to_list(self):
        return [url.toString() for url in self._items]


class AudioPlayer(QObject):
    """Ядро воспроизведения аудио."""
    posChanged = Signal(int)          # ms
    durChanged = Signal(int)          # ms
    stateChanged = Signal(QMediaPlayer.PlaybackState)
    metaDataChanged = Signal(dict)
    trackFinished = Signal(str, str)  # title, source
    errorOccurred = Signal(str)

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player = QMediaPlayer()
        self._audio_output = QAudioOutput()
        self._player.setAudioOutput(self._audio_output)

        self.playlist = PlaylistManager()
        self.playlist.currentIndexChanged.connect(self._on_playlist_index_changed)

        # Подключаем сигналы плеера к нашим слотам
        self._player.positionChanged.connect(self._on_position_changed)
        self._player.durationChanged.connect(self._on_duration_changed)
        self._player.playbackStateChanged.connect(self.stateChanged)
        self._player.metaDataChanged.connect(self._on_meta_data_changed)
        self._player.mediaStatusChanged.connect(self._on_media_status_changed)
        self._player.errorOccurred.connect(self._on_error)

        self._current_title = ""
        self._current_source = ""

    def _on_position_changed(self, pos):
        self.posChanged.emit(pos)

    def _on_duration_changed(self, dur):
        self.durChanged.emit(dur)

    def play(self):
        self._player.play()

    def pause(self):
        self._player.pause()

    def stop(self):
        self._player.stop()

    def set_volume(self, volume: int):
        self._audio_output.setVolume(volume / 100.0)

    def set_position(self, position_ms: int):
        self._player.setPosition(position_ms)

    def set_media(self, source, is_local=True):
        """Загрузить медиа (локальный путь или URL)."""
        if is_local:
            url = QUrl.fromLocalFile(source)
        else:
            url = QUrl(source)
        self._player.setSource(url)
        self._current_source = source
        self._current_title = source if not is_local else source.split('/')[-1]

    def play_playlist_at(self, index):
        """Воспроизвести трек из плейлиста по индексу."""
        if 0 <= index < self.playlist.mediaCount():
            url = self.playlist.media(index)
            self._player.setSource(url)
            self._current_source = url.toString()
            self._current_title = url.fileName() if url.isLocalFile() else url.toString()
            self.playlist.setCurrentIndex(index)
            self.play()

    def next_in_playlist(self):
        if self.playlist.next():
            url = self.playlist.currentMedia()
            self._player.setSource(url)
            self._current_source = url.toString()
            self._current_title = url.fileName() if url.isLocalFile() else url.toString()
            self.play()

    def previous_in_playlist(self):
        if self.playlist.previous():
            url = self.playlist.currentMedia()
            self._player.setSource(url)
            self._current_source = url.toString()
            self._current_title = url.fileName() if url.isLocalFile() else url.toString()
            self.play()

    def _on_playlist_index_changed(self, index):
        # Можно игнорировать, используется для GUI
        pass

    def _on_meta_data_changed(self):
        data = {}
        if self._player.metaData().keys():
            for key in self._player.metaData().keys():
                data[key] = self._player.metaData().stringValue(key)
            title = data.get(QMediaMetaData.Title, self._current_title)
            self._current_title = title
        self.metaDataChanged.emit(data)

    def _on_media_status_changed(self, status):
        if status == QMediaPlayer.EndOfMedia:
            self.trackFinished.emit(self._current_title, self._current_source)
            # Автоматически перейти к следующему треку, если есть плейлист
            if self.playlist.mediaCount() > 0:
                self.next_in_playlist()

    def _on_error(self, error, error_string):
        self.errorOccurred.emit(error_string)

    def is_playing(self):
        return self._player.playbackState() == QMediaPlayer.PlayingState

    def position(self):
        return self._player.position()

    def duration(self):
        return self._player.duration()

    def current_media_info(self):
        return self._current_title, self._current_source