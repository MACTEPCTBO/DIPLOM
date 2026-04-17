from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtMultimedia import QMediaPlayer, QAudioOutput
from models import Track


class AudioController(QObject):
    position_changed = Signal(int)
    duration_changed = Signal(int)
    state_changed = Signal(QMediaPlayer.PlaybackState)
    track_changed = Signal(Track)
    track_finished = Signal()
    error_occurred = Signal(str)

    def __init__(self):
        super().__init__()
        self.audio_output = QAudioOutput()
        self.player = QMediaPlayer()
        self.player.setAudioOutput(self.audio_output)
        self.audio_output.setVolume(0.7)

        self.player.positionChanged.connect(self._on_position_changed)
        self.player.durationChanged.connect(self._on_duration_changed)
        self.player.playbackStateChanged.connect(self._on_state_changed)
        self.player.errorOccurred.connect(self._on_error)
        self.player.mediaStatusChanged.connect(self._on_media_status_changed)

        self.current_track: Track = None

    def _on_position_changed(self, pos: int):
        self.position_changed.emit(pos)

    def _on_duration_changed(self, duration: int):
        self.duration_changed.emit(duration)

    def _on_state_changed(self, state: QMediaPlayer.PlaybackState):
        self.state_changed.emit(state)

    def _on_error(self, error, error_string: str):
        self.error_occurred.emit(error_string)

    def _on_media_status_changed(self, status: QMediaPlayer.MediaStatus):
        if status == QMediaPlayer.EndOfMedia:
            self.track_finished.emit()

    def play_track(self, track: Track):
        self.player.stop()
        self.player.setSource(QUrl())   # Сброс источника
        self.current_track = track
        if track.is_local:
            url = QUrl.fromLocalFile(track.url)
        else:
            url = QUrl(track.url)
        self.player.setSource(url)
        self.player.play()
        self.track_changed.emit(track)

    def toggle_play_pause(self):
        if self.player.playbackState() == QMediaPlayer.PlayingState:
            self.player.pause()
        else:
            self.player.play()

    def stop(self):
        self.player.stop()

    def set_volume(self, volume: int):
        self.audio_output.setVolume(volume / 100.0)

    def set_position(self, pos: int):
        self.player.setPosition(pos)