from PyQt5.QtCore import QTimer, QElapsedTimer, Qt
from PyQt5.QtWidgets import QApplication, QLabel, QPushButton, QVBoxLayout, QWidget

class Stopwatch(QWidget):
    def __init__(self):
        super().__init__()

        # Initialize the QTimer and QElapsedTimer
        self.timer = QTimer()
        self.timer.setTimerType(Qt.PreciseTimer)  # Use precise timer
        self.elapsed_timer = QElapsedTimer()      # To measure actual elapsed time

        # Label to display time
        self.time_display = QLabel("0.0 s", self)

        # Layout setup
        layout = QVBoxLayout()
        layout.addWidget(self.time_display)
        self.setLayout(layout)

        # Connect timer to update function
        self.timer.timeout.connect(self.update_time_display)

    def start_stopwatch(self):
        """Start the stopwatch."""
        if not self.timer.isActive():
            # Start the elapsed timer to record time and QTimer for periodic updates
            self.elapsed_timer.start()
            self.timer.start(100)  # 100 ms interval

    def stop_reset_stopwatch(self):
        """Stop or reset the stopwatch."""
        if self.timer.isActive():
            # Stop without resetting
            self.timer.stop()
        else:
            # Reset elapsed time and update display
            self.elapsed_timer.invalidate()  # Resets the elapsed timer
            self.time_display.setText("0.0 s")

    def update_time_display(self):
        """Update display based on actual elapsed time."""
        # Display actual elapsed time in seconds with one decimal place
        elapsed_seconds = self.elapsed_timer.elapsed() / 1000.0
        self.time_display.setText(f"{elapsed_seconds:.1f} s")