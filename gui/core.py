from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool
from gui.connection import GetConnectionWorker

class GPTSovitsCore(QObject):
    updateConnectionStatus = pyqtSignal(str)

    def __init__(self):
        super().__init__()
        self.host = None
        self.thread_pool = QThreadPool()
        
    def try_connect(self,
        host : str):
        worker = GetConnectionWorker(host)
        def lam1(h):
            self.host = h

        worker.emitters.updateHost.connect(lam1)
        worker.emitters.updateStatus.connect(lambda status: 
        self.updateConnectionStatus.emit(status))

        self.thread_pool.start(worker)
