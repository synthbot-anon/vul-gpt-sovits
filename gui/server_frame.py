from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout,
    QHBoxLayout, QLineEdit, QFrame, QLabel,
    QPushButton)
from gui.core import GPTSovitsCore
from gui.util import qshrink
from gui.stopwatch import Stopwatch

class ServerFrame(QGroupBox):
    def __init__(self, core: GPTSovitsCore):
        super().__init__(title="Server")
        self.setStyleSheet("QGroupBox { font: bold; }")
        
        l1 = QVBoxLayout(self)
        f1 = QFrame()
        qshrink(l1, 8)
        l1.addWidget(f1)
        
        l2 = QHBoxLayout(f1)
        qshrink(l2, 4)
        l2.addWidget(QLabel("Enter server host: "))
        l2.addStretch()
        self.le = QLineEdit()
        self.le.setFixedWidth(300)
        l2.addWidget(self.le)
        
        self.pb = QPushButton("Connect")
        l2.addWidget(self.pb)

        sf = QFrame()
        sfl = QHBoxLayout(sf)
        qshrink(sfl)
        self.status_label = QLabel("Connection status: N/A")
        self.stopwatch = Stopwatch()
        sfl.addWidget(self.status_label)
        sfl.addWidget(self.stopwatch)
        l1.addWidget(sf)
        
        self.core = core
        core.updateConnectionStatus.connect(
            lambda t: self.status_label.setText(
                f"Connection status: {t}"))
        core.connectionBusy.connect(
            lambda busy: self.pb.setEnabled(not busy))

        def update_stopwatch(ready: bool):
            if not ready: # Starting connection
                # Reset stopwatch
                self.stopwatch.stop_reset_stopwatch()
                self.stopwatch.start_stopwatch()
            else:
                # Stop stopwatch
                self.stopwatch.stop_reset_stopwatch()
        core.hostReady.connect(update_stopwatch)

        self.pb.clicked.connect(
            self.try_connect_cb)
        
    def try_connect_cb(self):
        self.core.try_connect(self.le.text())