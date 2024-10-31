import sys
from PyQt5.QtWidgets import (
    QApplication, QMainWindow, QVBoxLayout, QFrame, QToolBar, QAction,
    QHBoxLayout)
from gui.core import GPTSovitsCore
from gui.model_selection import ModelSelection
from gui.ref_audios import RefAudiosFrame
from gui.model_download import ModelDownload
from gui.inference import InferenceFrame
from gui.mega_browse import MegaBrowser

class CentralWidget(QFrame):
    def __init__(self, core: GPTSovitsCore):
        super().__init__()
        self.core = core
        l1 = QHBoxLayout(self)

        lf = QFrame()
        l2 = QVBoxLayout(lf)
        ms = ModelSelection(core)
        l2.addWidget(ms)
        raf = RefAudiosFrame(core)
        l2.addWidget(raf)

        l1.addWidget(lf)

        _if = InferenceFrame(core)
        l1.addWidget(_if)

class GPTSoVITSClient(QMainWindow):
    def __init__(self, core : GPTSovitsCore):
        super().__init__()
        self.setWindowTitle("GPT SoVITS GUI")
        self.show()
        
        self.core = core

        # Toolbar
        self.toolbar = QToolBar()
        self.addToolBar(self.toolbar)

        # Model download dialog
        def model_dialog():
            dialog = ModelDownload(core=self.core, parent=self)
            dialog.exec_()

        # Attempt to resize larger
        self.resize(1500, 1000)

        self.model_download = QAction("Add model", self)
        self.model_download.triggered.connect(model_dialog)
        self.model_download.setEnabled(True)
        self.toolbar.addAction(self.model_download)

        self.ref_audio_download = QAction("Master file downloader", self)
        def ref_audio_dl_dialog():
            dialog = MegaBrowser(core=self.core, parent=self)
            dialog.exec_()
        self.ref_audio_download.triggered.connect(ref_audio_dl_dialog)
        self.toolbar.addAction(self.ref_audio_download)

        # Central widget
        self.central_widget = CentralWidget(self.core)
        self.setCentralWidget(self.central_widget)
        