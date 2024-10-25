import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QFrame, QToolBar, QAction,
    QHBoxLayout)
from gui.core import GPTSovitsCore
from gui.server_frame import ServerFrame
from gui.model_selection import ModelSelection
from gui.ref_audios import RefAudiosFrame
from gui.model_download import ModelDownload
from gui.inference import InferenceFrame

class CentralWidget(QFrame):
    def __init__(self, core: GPTSovitsCore):
        super().__init__()
        self.core = core
        l1 = QHBoxLayout(self)

        lf = QFrame()
        l2 = QVBoxLayout(lf)
        sf = ServerFrame(core)
        l2.addWidget(sf)
        ms = ModelSelection(core)
        l2.addWidget(ms)
        raf = RefAudiosFrame(core)
        l2.addWidget(raf)

        l1.addWidget(lf)

        _if = InferenceFrame(core)
        l1.addWidget(_if)

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

        self.model_download = QAction("Add model to server", self)
        self.model_download.triggered.connect(model_dialog)
        self.toolbar.addAction(self.model_download)
        
        # Central widget
        self.central_widget = CentralWidget(self.core)
        self.setCentralWidget(self.central_widget)
        