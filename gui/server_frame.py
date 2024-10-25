from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout,
    QHBoxLayout, QLineEdit, QFrame, QLabel,
    QPushButton)
from gui.core import GPTSovitsCore
from gui.util import qshrink

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

        self.status_label = QLabel("Connection status: N/A")
        l1.addWidget(self.status_label)
        
        self.core = core
        core.updateConnectionStatus.connect(
            lambda t: self.status_label.setText(
                f"Connection status: {t}"))
        core.connectionBusy.connect(
            lambda busy: self.pb.setEnabled(not busy))

        self.pb.clicked.connect(
            self.try_connect_cb)
        #self.le.editingFinished.connect(self.edit_finished_cb)
        
    def try_connect_cb(self):
        self.core.try_connect(self.le.text())