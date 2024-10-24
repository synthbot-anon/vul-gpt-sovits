import sys
from PyQt5.QtWidgets import QApplication, QMainWindow, QVBoxLayout, QFrame
from gui.core import GPTSovitsCore
from gui.server_frame import ServerFrame
from gui.model_selection import ModelSelection
from gui.ref_audios import RefAudiosFrame

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
        self.central_widget = CentralWidget(self.core)
        self.setCentralWidget(self.central_widget)
        