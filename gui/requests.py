from PyQt5.QtCore import (QObject, QRunnable, pyqtSignal)
from logging import error
import httpx

class GetWorkerEmitters(QObject):
    gotResult = pyqtSignal(dict)
    error = pyqtSignal(dict)

class GetWorker(QRunnable):
    def __init__(self, host : str, route : str = "/route",
        timeout : float = None):
        super().__init__()
        self.host = host
        self.route = route
        self.emitters = GetWorkerEmitters()
        self.timeout = timeout

    # Should already used fixed ver of host from GetConnectionWorker
    def run(self):
        url = f"{self.host}{self.route}"
        try:
            response = httpx.get(url, timeout=self.timeout)
            if response.status_code == 200:
                self.emitters.gotResult.emit(response.json())
        except httpx.RequestError as e:
            error(f"Error: {e}")
            self.emitters.error.emit({'error': str(e)})

class PostWorkerEmitters(QObject):
    gotResult = pyqtSignal(dict)
    error = pyqtSignal(dict)

class PostWorker(QRunnable):
    def __init__(self, host : str, route : str, data : dict, 
        timeout : float = None):
        super().__init__()
        self.host = host
        self.route = route
        self.data = data
        self.emitters = PostWorkerEmitters()
        self.timeout = timeout

    def run(self):
        url = f"{self.host}{self.route}"
        try:
            response = httpx.post(url, json=self.data, timeout=self.timeout)
            if response.status_code == 200:
                if response.json() is not None:
                    self.emitters.gotResult.emit(response.json())
            else:
                self.emitters.error.emit({'error': f'status code {response.status_code}'})
        except httpx.RequestError as e:
            error(f"Error: {e}")
            self.emitters.error.emit({'error': str(e)})