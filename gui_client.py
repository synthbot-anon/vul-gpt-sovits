
import sys
from PyQt5.QtWidgets import QApplication
from gui.mainwindow import GPTSoVITSClient
        
if __name__ == '__main__':
    app = QApplication(sys.argv)
    window = GPTSoVITSClient()
    window.show()
    sys.exit(app.exec_())