from PyQt5.QtCore import QObject, pyqtSignal, QRunnable
import httpx

class GetConnectionWorkerEmitters(QObject):
    isBusy = pyqtSignal(bool)
    updateHost = pyqtSignal(str)
    updateStatus = pyqtSignal(str)
    error = pyqtSignal()

class GetConnectionWorker(QRunnable):
    def __init__(self, host : str):
        super().__init__()
        self.host = host
        self.emitters = GetConnectionWorkerEmitters()

    def run(self):
        self.emitters.isBusy.emit(True)
        host = self.host
        host = host.strip()
        self.emitters.updateStatus.emit(
            f"Attempting to connect to {host}"
        )
        
        head_url = f"{host}/test"
        try:
            response = httpx.head(head_url)
            if response.status_code == 200:
                self.host = host
                self.emitters.updateHost.emit(host)
                self.emitters.updateStatus.emit(
                    f"Successfully connected to {host}")
            else:
                self.host = None
                self.emitters.updateStatus.emit(
                    f"Host connection failed with status {response.status_code}"
                )
                self.emitters.error.emit()
        except (httpx.RequestError, httpx.InvalidURL) as e:
            self.emitters.updateStatus.emit(
                f"Error connecting: {e}"
            )
            self.host = None
            self.emitters.error.emit()
        finally:
            self.emitters.isBusy.emit(False)