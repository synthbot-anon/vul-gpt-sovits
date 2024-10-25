from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool
from gui.connection import GetConnectionWorker
from gui.default_config import default_config
from omegaconf import OmegaConf
from gui.database import GPTSovitsDatabase, CLIENT_DB_FILE, RefAudio

class GPTSovitsCore(QObject):
    updateConnectionStatus = pyqtSignal(str)
    updateHost = pyqtSignal(str, bool)
    hostReady = pyqtSignal(bool)
    connectionBusy = pyqtSignal(bool)
    newModelsAvailable = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.host = None
        self.is_local : bool = False
        self.thread_pool = QThreadPool()
        self.cfg = OmegaConf.create(default_config)
        self.database = GPTSovitsDatabase(db_file=CLIENT_DB_FILE)
        self.hashesSelectedSet = set()
        
    def try_connect(self,
        host : str):
        worker = GetConnectionWorker(host)
        self.hostReady.emit(False)
        def lam1(h):
            self.host = h
            self.is_local = ('127.0.0.1' in h or 'localhost' in h)
            self.updateHost.emit(self.host, self.is_local)
            if len(self.host):
                self.hostReady.emit(True)

        worker.emitters.updateHost.connect(lam1)
        worker.emitters.updateStatus.connect(lambda status: 
        self.updateConnectionStatus.emit(status))
        worker.emitters.isBusy.connect(self.connectionBusy)

        self.thread_pool.start(worker)
