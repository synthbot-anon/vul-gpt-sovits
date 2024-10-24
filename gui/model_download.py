from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QFrame, QHBoxLayout
)
from PyQt5.QtCore import (Qt, QRunnable, QObject, pyqtSignal, QThreadPool)
from gui.model_utils import find_models_hf
from gui.core import GPTSovitsCore

class FetchModelsWorkerEmitters(QObject):
    finished = pyqtSignal(dict)

class FetchModelsWorker(QRunnable):
    def __init__(self, repo : str):
        super().__init__()
        repo = repo.strip()
        self.repo = repo
        self.emitters = FetchModelsWorkerEmitters()

    def run(self):
        try:
            self.emitters.finished.emit(find_models_hf(self.repo))
        except Exception as e:
            self.emitters.finished.emit({'error': str(e)})

class ModelDownload(QDialog):
    updateRepo = pyqtSignal(dict)
    modelsDownloaded = pyqtSignal()
    def __init__(self, core: GPTSovitsCore, parent=None):
        super().__init__(parent)
        l1 = QVBoxLayout()
        
        hf_frame = QFrame()
        lhf = QHBoxLayout(hf_frame)
        self.hf_repo_edit = QLineEdit()
        lhf.addWidget(QLabel("HF Repo: "))
        lhf.addWidget(self.hf_repo_edit)
        self.hf_repo_edit.editingFinished.connect(
            self.repo_edit_finished
        )

        l1.addWidget(hf_frame)

        cb_frame = QFrame()
        lcb = QHBoxLayout(cb_frame)
        self.models_cb = QComboBox()
        self.models_cb.setFixedWidth(200)
        lcb.addWidget(QLabel("Models: "))
        lcb.addWidget(self.models_cb)

        self.add_button = QPushButton("Add to server")
        lcb.addWidget(self.add_button)

        l1.addWidget(cb_frame)

        self.thread_pool = QThreadPool()
        self.setLayout(l1)

    def update_repo_data(self, data : dict):
        if 'error' in data:
            self.models_cb.clear()
            return
        self.models_cb.clear()
        for model_name,model_data in data.items():
            self.models_cb.addItem(model_name, userData = model_data)

    def repo_edit_finished(self):
        text = self.hf_repo_edit.text().strip()
        if not len(text):
            return
        worker = FetchModelsWorker(text)
        worker.emitters.finished.connect(self.update_repo_data)
        self.thread_pool.start(worker)