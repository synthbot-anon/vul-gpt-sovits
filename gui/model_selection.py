from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QFrame, QPushButton, QStyle)
from PyQt5.QtCore import (QObject, QRunnable, QThreadPool, pyqtSignal)
from gui.core import GPTSovitsCore
from gui.util import qshrink
from gui.requests import GetWorker, PostWorker
from typing import Optional
from logging import error
import httpx

class ModelSelection(QGroupBox):
    modelsReady = pyqtSignal(bool)
    def __init__(self, core: GPTSovitsCore):
        super().__init__(title="Model selection")
        self.setStyleSheet("QGroupBox { font: bold; }")
        self.core = core
        self.modelsReady.connect(self.core.modelsReady)
        l1 = QVBoxLayout(self)
        qshrink(l1, 8)

        f1 = QFrame()
        l1.addWidget(f1)
        f1l = QHBoxLayout(f1)
        qshrink(f1l,4)
        f1l.addWidget(QLabel("Standalone SoVITS Weights: "))
        f1f = QFrame()
        f1l.addWidget(f1f)
        self.sovits_weights_lay = QVBoxLayout(f1f)
        qshrink(self.sovits_weights_lay)

        f2 = QFrame()
        l1.addWidget(f2)
        f2l = QHBoxLayout(f2)
        qshrink(f2l,4)
        f2l.addWidget(QLabel("Standalone GPT Weights: "))
        f2f = QFrame()
        f2l.addWidget(f2f)
        self.gpt_weights_lay = QVBoxLayout(f2f)
        qshrink(self.gpt_weights_lay)

        f3 = QFrame()
        l1.addWidget(f3)
        f3l = QHBoxLayout(f3)
        qshrink(f3l,4)
        f3l.addWidget(QLabel("Folderized weights: "))
        f3f = QFrame()
        f3l.addWidget(f3f)
        self.folder_weights_lay = QVBoxLayout(f3f)
        qshrink(self.folder_weights_lay)

        sync = QFrame()
        synclay = QHBoxLayout(sync)
        qshrink(synclay)
        sync_button = QPushButton("Sync available model list")
        sync_button.setIcon(
            self.style().standardIcon(
                getattr(QStyle, 'SP_BrowserReload')
            )
        )
        sync_button.setEnabled(False)
        self.core.hostReady.connect(self.retrieve_models)
        self.core.newModelsAvailable.connect(
            lambda: self.retrieve_models(True))
        synclay.addWidget(sync_button)
        self.sync_button = sync_button
        self.sync_button.clicked.connect(
            lambda: self.retrieve_models(True))
        load_button = QPushButton("Load selected models")
        load_button.setEnabled(False)
        load_button.clicked.connect(lambda: self.set_models({
            'sovits_path': self.sovits_weights_cb.currentText(),
            'gpt_path': self.gpt_weights_cb.currentText(),
        }))
        synclay.addWidget(load_button)
        self.load_button = load_button
        l1.addWidget(sync)

        self.sovits_weights_cb = QComboBox()
        self.sovits_weights_lay.addWidget(self.sovits_weights_cb)
        self.gpt_weights_cb = QComboBox()
        self.gpt_weights_lay.addWidget(self.gpt_weights_cb)
        self.folder_weights_cb = QComboBox()
        self.folder_weights_lay.addWidget(self.folder_weights_cb)

        def update_other_cbs():
            data = self.folder_weights_cb.currentData()
            sovits_path = data['sovits_weight']
            gpt_path = data['gpt_weight']
            self.sovits_weights_cb.setCurrentText(sovits_path)
            self.gpt_weights_cb.setCurrentText(gpt_path)

        self.folder_weights_cb.currentIndexChanged.connect(
            update_other_cbs)

        self.thread_pool = QThreadPool()
        self.modelsReady.connect(
            self.update_ready
        )
        self.models_label = QLabel("Models loaded: GPT (None), SOVITS (None)")
        l1.addWidget(self.models_label)
        self.update_ui_with_models()


    def update_ready(self, ready : bool):
        self.sovits_weights_cb.setEnabled(ready)
        self.gpt_weights_cb.setEnabled(ready)
        self.folder_weights_cb.setEnabled(ready)
        self.sync_button.setEnabled(ready)
        self.load_button.setEnabled(ready)

    def retrieve_models(self, ready : bool = False):
        if not ready:
            return
        self.modelsReady.emit(False)
        self.models_label.setText("Fetching available models from server...")
        def lam1(data):
            self.modelsReady.emit(True)
            self.models_label.setText("Got available models")
            self.update_ui_with_models(data)
        worker = GetWorker(host=self.core.host, route="/find_models")
        worker.emitters.gotResult.connect(lam1)
        self.thread_pool.start(worker)

    def set_models(self, data : dict):
        self.models_label.setText("Requesting model load...")
        self.modelsReady.emit(False)
        def lam1(data):
            self.modelsReady.emit(True)
            self.update_ui_loaded_models(data)
        worker = PostWorker(host=self.core.host, route="/set_models", data=data)
        worker.emitters.gotResult.connect(lam1)
        self.thread_pool.start(worker)

    def update_ui_loaded_models(self, data : dict):
        self.models_label.setText(
            f"Models loaded: GPT ({data['gpt_path']}), SOVITS ({data['sovits_path']})")

    def update_ui_with_models(self, data : Optional[dict] = None):
        self.sovits_weights_cb.clear()
        self.gpt_weights_cb.clear()
        self.folder_weights_cb.clear()

        if data is None:
            return

        loose_models : dict = data['loose_models']
        sovits_loose : list = loose_models['sovits_weights']
        gpt_loose : list = loose_models['gpt_weights']
        folder_models : list = data['folder_models']
        
        for model_name in sovits_loose:
            self.sovits_weights_cb.addItem(
                model_name)
        for model_name in gpt_loose:
            self.gpt_weights_cb.addItem(
                model_name)
        for model_dict in folder_models:
            model_name = model_dict['model_name']
            self.folder_weights_cb.addItem(
                model_name, userData=model_dict)