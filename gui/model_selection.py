from PyQt5.QtWidgets import (QGroupBox, QVBoxLayout, QHBoxLayout, 
    QLabel, QComboBox, QFrame, QPushButton, QStyle)
from PyQt5.QtCore import (QObject, QRunnable, QThreadPool, pyqtSignal, Qt)
from gui.compact_combo_box import CompactComboBox
from gui.core import GPTSovitsCore, now_dir
from gui.util import qshrink
from gui.stopwatch import Stopwatch
from gui.model_utils import find_models
from typing import Optional
from logging import error
from pathlib import Path
from TTS_infer_pack.TTS import TTS, TTS_Config
import httpx
import os

class ModelLoadWorkerEmitters(QObject):
    finished = pyqtSignal(dict)

class ModelLoadWorker(QRunnable):
    def __init__(self, 
        data : dict,
        core : GPTSovitsCore):
        super().__init__()
        self.data = data
        self.core = core
        self.emitters = ModelLoadWorkerEmitters()

    def run(self):
        self.core.tts_pipeline : TTS
        tts_pipeline = self.core.tts_pipeline
        info = self.data
        tts_pipeline.init_t2s_weights(
            info.get('gpt_path', None))
        tts_pipeline.init_vits_weights(
            info.get('sovits_path', None))
        self.emitters.finished.emit({
            'gpt_path': tts_pipeline.configs.t2s_weights_path,
            'sovits_path': tts_pipeline.configs.vits_weights_path
        })

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
        f1l.addWidget(QLabel("SoVITS Weights: "))
        f1f = QFrame()
        f1l.addWidget(f1f)
        self.sovits_weights_lay = QVBoxLayout(f1f)
        qshrink(self.sovits_weights_lay)

        f2 = QFrame()
        l1.addWidget(f2)
        f2l = QHBoxLayout(f2)
        qshrink(f2l,4)
        f2l.addWidget(QLabel("GPT Weights: "))
        f2f = QFrame()
        f2l.addWidget(f2f)
        self.gpt_weights_lay = QVBoxLayout(f2f)
        qshrink(self.gpt_weights_lay)

        f3 = QFrame()
        l1.addWidget(f3)
        f3l = QHBoxLayout(f3)
        qshrink(f3l,4)
        f3l.addWidget(QLabel("Speaker bundled weights: "))
        f3f = QFrame()
        f3l.addWidget(f3f)
        self.folder_weights_lay = QVBoxLayout(f3f)
        qshrink(self.folder_weights_lay)

        sync = QFrame()
        refresh_button = QPushButton("Refresh available models")
        refresh_button.setIcon(
            self.style().standardIcon(
                getattr(QStyle, 'SP_BrowserReload')
            )
        )
        synclay = QHBoxLayout(sync)
        synclay.addWidget(refresh_button)
        self.refresh_button = refresh_button
        self.refresh_button.clicked.connect(
            lambda: self.retrieve_available_models())
        load_button = QPushButton("Load selected models")
        load_button.clicked.connect(lambda: self.set_models({
            'sovits_path': self.sovits_weights_cb.currentText(),
            'gpt_path': self.gpt_weights_cb.currentText(),
        }))
        synclay.addWidget(load_button)
        self.load_button = load_button
        l1.addWidget(sync)

        self.sovits_weights_cb = CompactComboBox(160)
        self.sovits_weights_cb.view().setTextElideMode(
            Qt.ElideLeft)
        #self.sovits_weights_cb.setMaximumWidth(100)
        self.sovits_weights_lay.addWidget(self.sovits_weights_cb)
        self.gpt_weights_cb = CompactComboBox(160)
        #self.gpt_weights_cb.setMaximumWidth(100)
        self.gpt_weights_lay.addWidget(self.gpt_weights_cb)
        self.folder_weights_cb = CompactComboBox(160)
        #self.folder_weights_cb.setMaximumWidth(100)
        self.folder_weights_lay.addWidget(self.folder_weights_cb)

        def update_other_cbs():
            data = self.folder_weights_cb.currentData()
            if data is None:
                return
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
        
        mf = QFrame()
        mfl = QHBoxLayout(mf)
        qshrink(mfl)
        self.models_label = QLabel("Models loaded: GPT (None), SOVITS (None)")
        self.models_label.setMaximumWidth(600)
        self.models_label.setWordWrap(True)
        self.stopwatch = Stopwatch()
        mfl.addWidget(self.models_label)
        mfl.addWidget(self.stopwatch)
        l1.addWidget(mf)
        self.core.newModelsAvailable.connect(
            lambda: self.retrieve_available_models())
        self.retrieve_available_models()
        self.retrieve_current_models()

    def update_ready(self, ready : bool):
        self.sovits_weights_cb.setEnabled(ready)
        self.gpt_weights_cb.setEnabled(ready)
        self.folder_weights_cb.setEnabled(ready)
        self.refresh_button.setEnabled(ready)
        self.load_button.setEnabled(ready)

    def retrieve_current_models(self):
        self.core.tts_pipeline : TTS
        tts_pipeline = self.core.tts_pipeline
        self.update_ui_loaded_models({
            'gpt_path': tts_pipeline.configs.t2s_weights_path,
            'sovits_path': tts_pipeline.configs.vits_weights_path
        })

    def retrieve_available_models(self):
        models = find_models(
            Path(now_dir),
            Path(now_dir) / 'models')
        self.update_ui_with_models(models)

    def set_models(self, data : dict):
        self.models_label.setText("Loading selected models...")
        self.modelsReady.emit(False)
        # Reset stopwatch
        self.stopwatch.stop_reset_stopwatch()
        self.stopwatch.start_stopwatch()
        def lam1(data):
            self.modelsReady.emit(True)
            # Stop stopwatch
            self.stopwatch.stop_reset_stopwatch()
            self.update_ui_loaded_models(data)

        worker = ModelLoadWorker(
            data=data, core=self.core)
        worker.emitters.finished.connect(lam1)
        self.thread_pool.start(worker)

    def update_ui_loaded_models(self, data : dict):
        self.models_label.setText(
            f"Models loaded: GPT ({os.path.basename(data['gpt_path'])})"
            f", SOVITS ({os.path.basename(data['sovits_path'])})")

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