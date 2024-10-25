from PyQt5.QtWidgets import (QWidget,
    QVBoxLayout, QLabel, QFrame, QHBoxLayout, QSlider, QSizePolicy,
    QStyle, QPushButton)
from PyQt5.QtCore import (
    QMimeData, QUrl, Qt, QByteArray, QBuffer, QRunnable, QObject, pyqtSignal
)
from PyQt5.QtGui import (
    QDrag, QPainter, QColor
)
from PyQt5.QtMultimedia import (
   QMediaContent, QAudio, QAudioDeviceInfo, QMediaPlayer)
import soundfile as sf
import os
import time
import numpy as np
import matplotlib.pyplot as plt
from io import BytesIO
from gui.util import qshrink

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
        self.pb.setFixedWidth(30)
        self.pb.setFixedHeight(20)
        self.pb.setSizePolicy(QSizePolicy.Minimum,
            QSizePolicy.Minimum)
        # self.pb.mouseMoveEvent = self.drag_hook
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

class WaveformDisplay(QFrame):
    def __init__(self, player, parent=None):
        super().__init__(parent)
        self.setMinimumHeight(100)
        self.waveform = None
        self.marker_position = 0
        self.duration = 0
        self.player = player

    def load_waveform(self, audio_data, downsample_factor=8000):
        samples, sample_rate = sf.read(BytesIO(audio_data))
        self.duration = len(samples) / sample_rate

        # Convert to mono if stereo
        if len(samples.shape) > 1:
            samples = samples.mean(axis=1)

        # Downsample by taking min and max of each chunk
        downsampled_waveform = []
        for i in range(0, len(samples), downsample_factor):
            chunk = samples[i:i+downsample_factor]
            min_val, max_val = chunk.min(), chunk.max()
            #downsampled_waveform.append(min_val)
            downsampled_waveform.append(max_val)

        # Normalize to fit widget height
        self.waveform = ((np.array(downsampled_waveform) - np.min(downsampled_waveform)) / 
                        (np.ptp(downsampled_waveform)) * (self.height() / 2)).astype(int)


        self.update()  # Trigger repaint

    def set_marker_position(self, position):
        self.marker_position = position
        self.update()

    def paintEvent(self, event):
        if self.waveform is None:
            return

        painter = QPainter(self)
        painter.setPen(Qt.NoPen)  # No border for rectangles
        painter.setBrush(QColor('green'))  # Set brush color for waveform rectangles

        pixel_spacing = 2  # Spacing between rectangles in pixels
        rect_width = (self.width() - pixel_spacing * (len(self.waveform) - 1)) / len(self.waveform)
        middle = self.height() // 2

        for i, amplitude in enumerate(self.waveform):
            # Calculate the height of each rectangle based on the already normalized amplitude
            rect_height = int(amplitude*0.2)

            # Calculate x position with spacing taken into account
            rect_x = int(i * (rect_width + pixel_spacing))

            # Draw the rectangle centered vertically
            painter.drawRect(rect_x, middle - rect_height, int(rect_width), rect_height * 2)

        # Draw play marker
        if self.duration > 0:
            marker_x = int(self.marker_position * self.width() / self.duration)
            painter.setBrush(QColor('red'))
            painter.drawRect(marker_x - 1, 0, 2, self.height())  # Draw a thin rectangle as marker


class RichAudioPreviewWidget(QWidget):
    def __init__(self, button_only=False, drag_enabled=True, pausable=True):
        super().__init__()

        hlayout = QHBoxLayout(self)
        frame = QFrame()
        hlayout.addWidget(frame)
        qshrink(hlayout)

        vlayout = QVBoxLayout(frame)
        vlayout.setSpacing(0)
        vlayout.setContentsMargins(0, 0, 0, 0)
        vlayout.setAlignment(Qt.AlignCenter)
        self.vlayout = vlayout

        # Player setup
        self.player = QMediaPlayer()
        self.player.setNotifyInterval(50)  # Higher update rate for smoother marker

        # Add waveform display
        self.waveform_display = WaveformDisplay(self.player)
        self.waveform_display.setSizePolicy(
            QSizePolicy.Expanding,
            QSizePolicy.Maximum
        )
        hlayout.addWidget(self.waveform_display)
        #self.vlayout.addWidget(self.waveform_display)

        # Play button
        self.play_button = QPushButton()
        self.play_button.setIcon(self.style().standardIcon(
            getattr(QStyle, 'SP_MediaPlay')
        ))
        self.play_button.clicked.connect(self.toggle_play)
        hlayout.addWidget(self.play_button)

        self.local_file = ""
        self.pausable = pausable
        self.mouse_over = False

        # Connections for slider and player
        self.player.positionChanged.connect(self.update_marker)
        self.player.stateChanged.connect(self.state_changed)

        if (drag_enabled):
            self.play_button.mouseMoveEvent = self.drag_hook
        self.waveform_display.mouseMoveEvent = self.waveform_move_event
        self.waveform_display.mouseClickEvent = self.waveform_move_event

    def enterEvent(self, event):
        """Triggered when the mouse enters the widget area."""
        self.mouse_over = True
        # Ensure the widget can receive keyboard focus
        self.setFocus()

    def leaveEvent(self, event):
        """Triggered when the mouse leaves the widget area."""
        self.mouse_over = False

    def keyPressEvent(self, event):
        """Handle key press events for the widget."""
        if self.mouse_over and event.key() == Qt.Key_Space:
            self.toggle_play()
            event.accept()  # Mark the event as handled
        else:
            super().keyPressEvent(event)  # Pass to base class for other keys

    def from_file(self, path):
        self.load_audio_waveform(path)
        self.player.setMedia(QMediaContent(QUrl.fromLocalFile(os.path.abspath(path))))
        self.local_file = path

    def from_memory(self, data):
        self.load_audio_waveform(data, from_memory=True)
        self.audio_data = QByteArray(data)
        self.audio_buffer = QBuffer()
        self.audio_buffer.setData(self.audio_data)
        self.audio_buffer.open(QBuffer.ReadOnly)
        self.player.setMedia(QMediaContent(), self.audio_buffer)

    def load_audio_waveform(self, audio_data, from_memory=False):
        # Load waveform data from file or memory
        if from_memory:
            self.waveform_display.load_waveform(audio_data)
        else:
            with open(audio_data, 'rb') as f:
                self.waveform_display.load_waveform(f.read())

    def state_changed(self, state):
        if (state == QMediaPlayer.StoppedState) or (
            state == QMediaPlayer.PausedState):
            self.play_button.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPlay')))

    def toggle_play(self):
        if self.player.state() == QMediaPlayer.PlayingState:
            self.player.pause() if self.pausable else self.player.stop()
        elif self.player.mediaStatus() != QMediaPlayer.NoMedia:
            self.player.play()
            self.play_button.setIcon(self.style().standardIcon(
                getattr(QStyle, 'SP_MediaPause')
            ))

    def seek(self, position):
        self.player.setPosition(position)

    def update_marker(self, position):
        self.waveform_display.set_marker_position(position / 1000)

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

    def waveform_move_event(self, event):
        # Calculate the click position as a percentage of the waveform width
        click_x = event.x()
        width = self.waveform_display.width()
        click_position_ratio = click_x / width
        if click_x < 0 or click_x > width:
            return

        # Calculate the new playback position in milliseconds
        new_position = int(click_position_ratio * float(self.waveform_display.duration) * 1000)

        # Update the audio player and the play marker
        self.player.setPosition(new_position)

        # Redraw the widget to update the play marker position
        self.update()
