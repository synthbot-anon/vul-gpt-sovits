from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool
from gui.connection import GetConnectionWorker
from gui.default_config import default_config, DEFAULT_CONFIG_PATH
from omegaconf import OmegaConf
from gui.database import GPTSovitsDatabase, CLIENT_DB_FILE, RefAudio
from pathlib import Path
from typing import Optional

class GPTSovitsCore(QObject):
    updateConnectionStatus = pyqtSignal(str)
    updateHost = pyqtSignal(str, bool)
    hostReady = pyqtSignal(bool)
    modelsReady = pyqtSignal(bool)
    connectionBusy = pyqtSignal(bool)
    connectionError = pyqtSignal()
    newModelsAvailable = pyqtSignal()
    databaseSelfUpdate = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.host = None
        self.is_local : bool = False
        self.thread_pool = QThreadPool()
        if not Path(DEFAULT_CONFIG_PATH).exists():
            self.cfg = OmegaConf.create(default_config)
        else:
            self.cfg = OmegaConf.load(DEFAULT_CONFIG_PATH)
        with open(DEFAULT_CONFIG_PATH, 'w') as f:
            f.write(OmegaConf.to_yaml(self.cfg))
        self.database = GPTSovitsDatabase(db_file=CLIENT_DB_FILE)
        self.auxSelectedSet = set()
        self.primaryRefHash = set()
        self.integrity_update()

    def integrity_update(self):
        if (self.database.integrity_update()):
            self.databaseSelfUpdate.emit()
        
    def try_connect(self,
        host : str):

        host = host.replace('0.0.0.0','127.0.0.1')
        # Localhost name resolution on Windows is slow
        host = host.replace('localhost','127.0.0.1')
        if not host.startswith('http') or host.startswith('https'):
            host = 'http://'+host
        if host.endswith('/'):
            host = host[:-1]

        worker = GetConnectionWorker(host)
        self.hostReady.emit(False)
        def lam1(h):
            self.host = h
            if h is not None:
                self.is_local = ('127.0.0.1' in h or 'localhost' in h)
            self.updateHost.emit(self.host, self.is_local)
            if len(self.host):
                self.hostReady.emit(True)

        worker.emitters.updateHost.connect(lam1)
        worker.emitters.updateStatus.connect(lambda status: 
        self.updateConnectionStatus.emit(status))
        worker.emitters.isBusy.connect(self.connectionBusy)
        worker.emitters.error.connect(self.connectionError)

        self.thread_pool.start(worker)
