from PyQt5.QtWidgets import QPushButton, QFileDialog
from PyQt5.QtCore import pyqtSignal

class FileButton(QPushButton):
    filesSelected = pyqtSignal(list)
    def __init__(self,
        label = "Files to Convert",
        dialog_title = "Select files",
        dialog_filter = "All Files (*);;Text Files (*.txt)"):
        super().__init__(label)
        self.setAcceptDrops(True)
        self.clicked.connect(self.loadFileDialog)
        self.dialog_title = dialog_title
        self.dialog_filter = dialog_filter
        
    def loadFileDialog(self):
        filenames, _ = QFileDialog.getOpenFileNames(
            self, self.dialog_title, "", self.dialog_filter
        )
        self.filesSelected.emit(filenames)

    def dragEnterEvent(self, event):
        if event.mimeData().hasUrls():
            event.accept()
        else:
            event.ignore()

    def dropEvent(self, event):
        if event.mimeData().hasUrls():
            files = []
            for url in event.mimeData().urls():
                if not url.toLocalFile():
                    continue
                files.append(url.toLocalFile())
            self.filesSelected.emit(files)
            event.acceptProposedAction()
        else:
            event.ignore()
        pass