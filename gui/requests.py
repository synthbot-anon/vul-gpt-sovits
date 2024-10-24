from PyQt5.QtCore import (QObject, QRunnable, pyqtSignal)

class GetWorkerEmitters(QObject):
    gotResult = pyqtSignal(dict)

class GetWorker(QRunnable):
    def __init__(self, host : str, route : str = "/route"):
        super().__init__()
        self.host = host
        self.route = route
        self.emitters = GetWorkerEmitters()

    # Should already used fixed ver of host from GetConnectionWorker
    def run(self):
        url = f"{self.host}{self.route}"
        try:
            response = httpx.get(url)
            if response.status_code == 200:
                self.emitters.gotResult.emit(response.json())
        except httpx.RequestError as e:
            error(f"Error retrieving models: {e}")

class PostWorkerEmitters(QObject):
    gotResult = pyqtSignal(dict)

class PostWorker(QRunnable):
    def __init__(self, host : str, route : str, data : dict):
        super().__init__()
        self.host = host
        self.route = route
        self.data = data
        self.emitters = PostWorkerEmitters()

    def run(self):
        url = f"{self.host}{self.route}"
        try:
            response = httpx.post(url, self.data)
            if response.status_code == 200:
                self.emitters.gotResult.emit(response.json())
        except httpx.RequestError as e:
            error(f"Error retrieving models: {e}")