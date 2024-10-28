from PyQt5.QtWidgets import (
    QDialog, QVBoxLayout, QLineEdit, QPushButton, QLabel,
    QComboBox, QFrame, QHBoxLayout
)
from PyQt5.QtCore import (Qt, QRunnable, QObject, pyqtSignal, QThreadPool)
from gui.model_utils import find_models_hf
from gui.core import GPTSovitsCore, now_dir
from gui.stopwatch import Stopwatch
from gui.util import qshrink
from pathlib import Path
import os
import huggingface_hub

class DownloadModelsWorkerEmitters(QObject):
    finished = pyqtSignal()
    error = pyqtSignal(str)

class DownloadModelsWorker(QRunnable):
    def __init__(self, 
        core : GPTSovitsCore,
        data : dict):
        super().__init__()
        self.data = data
        self.core = core
        self.emitters = DownloadModelsWorkerEmitters()

    def run(self):
        info = self.data
        models_dir = Path(now_dir) / self.core.cfg.models_dir
        model_dir : Path = models_dir / info['model_name']
        strmodel_dir = str(model_dir.absolute())
        if not model_dir.exists():
            os.makedirs(strmodel_dir)
        try:
            huggingface_hub.hf_hub_download(
                repo_id = info['repo'],
                filename = info['gpt_path'],
                local_dir = models_dir
            )
            huggingface_hub.hf_hub_download(
                repo_id = info['repo'],
                filename = info['sovits_path'],
                local_dir = models_dir
            )
            self.emitters.finished.emit()
        except Exception as e:
            self.emitters.error.emit(str(e))
            return

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
        self.hf_repo_edit = QLineEdit("therealvul/GPT-SoVITS-v2")
        lhf.addWidget(QLabel("HF Repo: "))
        lhf.addWidget(self.hf_repo_edit)
        self.hf_repo_edit.editingFinished.connect(
            self.repo_edit_finished
        )

        l1.addWidget(hf_frame)

        cb_frame = QFrame()
        lcb = QHBoxLayout(cb_frame)
        self.models_cb = QComboBox()
        self.models_cb.setFixedWidth(300)
        lcb.addWidget(QLabel("Models: "))
        lcb.addWidget(self.models_cb)

        self.core = core

        self.add_button = QPushButton("Add to server")
        self.add_button.clicked.connect(self.request_add)
        self.add_button.setEnabled(False)
        lcb.addWidget(self.add_button)

        l1.addWidget(cb_frame)

        self.thread_pool = QThreadPool()
        sf = QFrame()
        sf_l = QHBoxLayout(sf)
        qshrink(sf_l)
        self.status = QLabel("Status")
        self.status.setWordWrap(True)
        self.status.setMaximumWidth(400)
        sf_l.addWidget(self.status)
        self.stopwatch = Stopwatch()
        sf_l.addWidget(self.stopwatch)
        l1.addWidget(sf)
        self.setLayout(l1)

        self.core = core
        self.modelsDownloaded.connect(self.core.newModelsAvailable)
        self.repo_edit_finished()

    def request_add(self):
        model_name : str = self.models_cb.currentText()
        data : dict = self.models_cb.currentData()
        if self.models_cb.currentData() is None:
            return
        self.status.setText(f"Requested download of {model_name}")
        self.stopwatch.start_stopwatch()
        worker = DownloadModelsWorker(
            core=self.core,
            data={
                'model_name': model_name,
                'repo': data['repo'],
                'gpt_path': data['gpt_weight'],
                'sovits_path': data['sovits_weight'],
            }
        )
        worker.emitters.finished.connect(self.modelsDownloaded)
        worker.emitters.finished.connect(lambda:
            self.stopwatch.stop_reset_stopwatch()
        )
        def handle_error(data):
            self.stopwatch.stop_reset_stopwatch()
            if 'error' in data:
                self.status.setText(f"Error: {data['error']}")
        worker.emitters.error.connect(handle_error)
        self.thread_pool.start(worker)

    def update_repo_data(self, data : dict):
        if 'error' in data:
            self.models_cb.clear()
            self.status.setText(f"Error: {data['error']}")
            return
        self.models_cb.clear()
        for model_name,model_data in data.items():
            model_data['repo'] = self.hf_repo_edit.text().strip()
            self.models_cb.addItem(model_name, userData = model_data)
        self.add_button.setEnabled(True)

    def repo_edit_finished(self):
        text = self.hf_repo_edit.text().strip()
        if not len(text):
            return
        self.add_button.setEnabled(False)
        worker = FetchModelsWorker(text)
        worker.emitters.finished.connect(self.update_repo_data)
        self.thread_pool.start(worker)