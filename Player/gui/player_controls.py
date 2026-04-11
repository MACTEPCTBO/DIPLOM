from PySide6.QtWidgets import (
    QWidget, QHBoxLayout, QPushButton, QSlider, QLabel, QStyle
)
from PySide6.QtCore import Qt
from PySide6.QtMultimedia import QMediaPlayer

class PlayerControls(QWidget):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.player = player

        layout = QHBoxLayout()
        layout.setSpacing(10)

        self.prev_btn = QPushButton()
        self.prev_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipBackward))
        self.prev_btn.clicked.connect(self.player.previous_in_playlist)
        self.prev_btn.setToolTip("Предыдущий")

        self.play_btn = QPushButton()
        self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))
        self.play_btn.clicked.connect(self._toggle_play)
        self.play_btn.setToolTip("Воспроизвести/Пауза")

        self.stop_btn = QPushButton()
        self.stop_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaStop))
        self.stop_btn.clicked.connect(self.player.stop)
        self.stop_btn.setToolTip("Стоп")

        self.next_btn = QPushButton()
        self.next_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaSkipForward))
        self.next_btn.clicked.connect(self.player.next_in_playlist)
        self.next_btn.setToolTip("Следующий")

        layout.addWidget(self.prev_btn)
        layout.addWidget(self.play_btn)
        layout.addWidget(self.stop_btn)
        layout.addWidget(self.next_btn)

        # Прогресс
        self.time_label = QLabel("00:00 / 00:00")
        layout.addWidget(self.time_label)

        self.position_slider = QSlider(Qt.Horizontal)
        self.position_slider.setRange(0, 0)
        self.position_slider.sliderMoved.connect(self.player.set_position)
        layout.addWidget(self.position_slider, stretch=1)

        # Громкость
        volume_label = QLabel("🔊")
        layout.addWidget(volume_label)
        self.volume_slider = QSlider(Qt.Horizontal)
        self.volume_slider.setRange(0, 100)
        self.volume_slider.setValue(80)
        self.volume_slider.valueChanged.connect(self.player.set_volume)
        self.volume_slider.setMaximumWidth(100)
        layout.addWidget(self.volume_slider)

        self.setLayout(layout)

        self.player.stateChanged.connect(self._update_play_button)
        self.player.posChanged.connect(self._update_position)
        self.player.durChanged.connect(self._update_duration)

    def _toggle_play(self):
        if self.player.is_playing():
            self.player.pause()
        else:
            self.player.play()

    def _update_play_button(self, state):
        if state == QMediaPlayer.PlayingState:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPause))
        else:
            self.play_btn.setIcon(self.style().standardIcon(QStyle.StandardPixmap.SP_MediaPlay))

    def _update_position(self, pos):
        self.position_slider.setValue(pos)
        self._update_time_label()

    def _update_duration(self, dur):
        self.position_slider.setRange(0, dur)
        self._update_time_label()

    def _update_time_label(self):
        pos = self.player.position()
        dur = self.player.duration()
        self.time_label.setText(f"{self._ms_to_str(pos)} / {self._ms_to_str(dur)}")

    @staticmethod
    def _ms_to_str(ms):
        s = ms // 1000
        m, s = divmod(s, 60)
        return f"{m:02d}:{s:02d}"