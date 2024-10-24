from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QFrame)
from gui.core import GPTSovitsCore
from gui.util import qshrink

class ModelSelection(QGroupBox):
    def __init__(self, core: GPTSovitsCore):
        super().__init__(title="Model selection")
        self.core = core
        l1 = QVBoxLayout(self)
        qshrink(l1)

        f1 = QFrame()
        l1.addWidget(f1)
        f1l = QHBoxLayout(f1)
        qshrink(f1l,4)
        f1l.addWidget(QLabel("Standalone SoVITS Weights: "))
        f1f = QFrame()
        f1l.addWidget(f1f)
        self.sovits_weights_lay = QVBoxLayout(f1f)

        f2 = QFrame()
        l1.addWidget(f2)
        f2l = QHBoxLayout(f2)
        qshrink(f2l,4)
        f2l.addWidget(QLabel("Standalone GPT Weights: "))
        f2f = QFrame()
        f2l.addWidget(f2f)
        self.gpt_weights_lay = QVBoxLayout(f2f)

        f3 = QFrame()
        l1.addWidget(f3)
        f3l = QHBoxLayout(f3)
        qshrink(f3l,4)
        f3l.addWidget(QLabel("Folderized weights: "))
        f3f = QFrame()
        f3l.addWidget(f3f)
        self.folder_weights_lay = QVBoxLayout(f3f)
        self.update_with_models()

    def update_with_models(self):
        if hasattr(self, 'sovits_weights_cb'):
            self.sovits_weights_cb.deleteLater()
            del self.sovits_weights_cb
        if hasattr(self, 'gpt_weights_cb'):
            self.gpt_weights_cb.deleteLater()
            del self.gpt_weights_cb
        if hasattr(self, 'folder_weights_cb'):
            self.folder_weights_cb.deleteLater()
            del self.folder_weights_cb
        if self.core.host is None:
            self.sovits_weights_cb = QComboBox()
            self.sovits_weights_lay.addWidget(self.sovits_weights_cb)

            self.gpt_weights_cb = QComboBox()
            self.gpt_weights_lay.addWidget(self.gpt_weights_cb)

            self.folder_weights_cb = QComboBox()
            self.folder_weights_lay.addWidget(self.folder_weights_cb)