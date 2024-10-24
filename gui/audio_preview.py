from PyQt5.QtWidgets import (QWidget,
    QVBoxLayout, QLabel, QFrame, QHBoxLayout, QSlider, QSizePolicy,
    QStyle, QPushButton)
from PyQt5.QtCore import (
    QMimeData, QUrl, Qt, QByteArray, QBuffer, QRunnable, QObject, pyqtSignal
)
from PyQt5.QtGui import (
    QDrag
)
from PyQt5.QtMultimedia import (
   QMediaContent, QAudio, QAudioDeviceInfo, QMediaPlayer)
import os
import time

class AudioPreviewWidget(QWidget):
    def __init__(self,
        button_only=False,
        drag_enabled=True,
        pausable=True):
        super().__init__()
        self.vlayout = QVBoxLayout(self)
        self.vlayout.setSpacing(0)
        self.vlayout.setContentsMargins(0,0,0,0)

        self.playing_label = QLabel("Preview")
        self.playing_label.setWordWrap(True)
        if (not button_only):
            self.vlayout.addWidget(self.playing_label)

        self.player_frame = QFrame()
        self.vlayout.addWidget(self.player_frame)

        self.player_layout = QHBoxLayout(self.player_frame)
        self.player_layout.setSpacing(4)
        self.player_layout.setContentsMargins(0,0,0,0)

        self.player = QMediaPlayer()
        self.player.setNotifyInterval(500)

        self.seek_slider = QSlider(Qt.Horizontal)
        self.seek_slider.setSizePolicy(QSizePolicy.Expanding,
            QSizePolicy.Preferred)

        if (not button_only):
            self.player_layout.addWidget(self.seek_slider)

        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_MediaPlay')))
        self.player_layout.addWidget(self.play_button)
        self.play_button.clicked.connect(self.toggle_play)
        self.play_button.setSizePolicy(QSizePolicy.Maximum,
            QSizePolicy.Minimum)
        if (drag_enabled):
            self.play_button.mouseMoveEvent = self.drag_hook

        self.seek_slider.sliderMoved.connect(self.seek)
        self.player.positionChanged.connect(self.update_seek_slider)
        self.player.stateChanged.connect(self.state_changed)
        self.player.durationChanged.connect(self.duration_changed)

        self.local_file = ""
        self.pausable = pausable

    def set_text(self, text=""):
        if len(text) > 0:
            self.playing_label.show()
            self.playing_label.setText(text)
        else:
            self.playing_label.hide()

    def from_file(self, path):
        try:
            self.player.stop()
            if hasattr(self, 'audio_buffer'):
                self.audio_buffer.close()

            self.player.setMedia(QMediaContent(QUrl.fromLocalFile(
                os.path.abspath(path))))

            self.play_button.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPlay')))

            self.local_file = path
        except Exception as e:
            print(e)
            pass

    def drag_hook(self, e):
        if e.buttons() != Qt.LeftButton:
            return
        if not len(self.local_file):
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(
            os.path.abspath(self.local_file))])
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)

    def from_memory(self, data):
        self.player.stop()
        if hasattr(self, 'audio_buffer'):
            self.audio_buffer.close()

        self.audio_data = QByteArray(data)
        self.audio_buffer = QBuffer()
        self.audio_buffer.setData(self.audio_data)
        self.audio_buffer.open(QBuffer.ReadOnly)
        player.setMedia(QMediaContent(), self.audio_buffer)

    def state_changed(self, state):
        if (state == QMediaPlayer.StoppedState) or (
            state == QMediaPlayer.PausedState):
            self.play_button.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPlay')))

    def duration_changed(self, dur):
        self.seek_slider.setRange(0, self.player.duration())

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            if self.pausable:
                self.player.pause()
            else:
                self.player.stop()
        elif self.player.mediaStatus() != QMediaPlayer.NoMedia:
            self.player.play()
            self.play_button.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPause')))

    def update_seek_slider(self, position):
        self.seek_slider.setValue(position)

    def seek(self, position):
        self.player.setPosition(position)

# Lighter weight version of the above:
#   - only loads media player/media when play button is pressed
#   - no pausing/resuming, just stopping
class SmallAudioPreviewWidget(QWidget):
    def __init__(self,
        local_file : str):
        super( ).__init__()
        self.pb = QPushButton()
        self.pb.setIcon(self.style().standardIcon(getattr(QStyle, 'SP_MediaPlay')))
        lay = QVBoxLayout(self)
        lay.addWidget(self.pb)
        self.pb.clicked.connect(self.toggle_play)
        self.pb.mouseMoveEvent = self.drag_hook
        self.local_file = local_file
        self.is_playing : bool = False

    def stop(self):
        if hasattr(self, 'player'):
            self.player : QMediaPlayer
            self.player.stop()
            self.player.deleteLater()
            del self.player
        self.is_playing = False

    def play(self):
        self.is_playing = True
        self.player = QMediaPlayer()
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(
            os.path.abspath(self.local_file))))
        self.player.play()
        self.player.stateChanged.connect(self.state_changed)

    def state_changed(self, state):
        if (state == QMediaPlayer.StoppedState):
            self.pb.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPlay')))
            self.is_playing = False

    def toggle_play(self):
        if self.is_playing:
            self.stop()
        else: 
            self.play()
            self.pb.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPause')))

    def drag_hook(self, e):
        if e.buttons() != Qt.LeftButton:
            return
        if not len(self.local_file):
            return

        mime_data = QMimeData()
        mime_data.setUrls([QUrl.fromLocalFile(
            os.path.abspath(self.local_file))])
        drag = QDrag(self)
        drag.setMimeData(mime_data)
        drag.exec_(Qt.CopyAction)