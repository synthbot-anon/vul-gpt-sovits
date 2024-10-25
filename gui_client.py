
import sys
from PyQt5.QtWidgets import QApplication
from gui.mainwindow import GPTSoVITSClient
import qdarktheme

def load_stylesheet(file_path):
    with open(file_path, "r") as f:
        return f.read()
        
if __name__ == '__main__':
    qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()
    window = GPTSoVITSClient()
    window.show()
    sys.exit(app.exec_())