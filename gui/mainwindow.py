import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QFrame, QToolBar, QAction)
from gui.core import GPTSovitsCore
from gui.server_frame import ServerFrame
from gui.model_selection import ModelSelection
from gui.ref_audios import RefAudiosFrame
from gui.model_download import ModelDownload

class CentralWidget(QFrame):
    def __init__(self, core: GPTSovitsCore):
        super().__init__()
        self.core = core
        l1 = QVBoxLayout(self)
        sf = ServerFrame(core)
        l1.addWidget(sf)
        ms = ModelSelection(core)
        l1.addWidget(ms)
        raf = RefAudiosFrame(core)
        l1.addWidget(raf)

class GPTSoVITSClient(QMainWindow):
    def __init__(self):
        super().__init__()
        self.setWindowTitle("GPT SoVITS Client")
        self.show()
        
        self.core = GPTSovitsCore()

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Model download dialog
        def model_dialog():
            dialog = ModelDownload(core=self.core, parent=self)
            dialog.exec_()

        self.model_download = QAction("Add Model", self)
        self.model_download.triggered.connect(model_dialog)
        self.toolbar.addAction(self.model_download)
        
        # Central widget
        self.central_widget = CentralWidget(self.core)
        self.setCentralWidget(self.central_widget)
        