
import sys
from PyQt5.QtWidgets import QApplication
from gui.mainwindow import GPTSoVITSClient
from gui.core import GPTSovitsCore
import qdarktheme

def load_stylesheet(file_path):
    with open(file_path, "r") as f:
        return f.read()
        
if __name__ == '__main__':
    core = GPTSovitsCore()
    if core.cfg.enable_hi_dpi:
        qdarktheme.enable_hi_dpi()
    app = QApplication(sys.argv)
    qdarktheme.setup_theme()

    screen = app.primaryScreen()
    screen_geometry = screen.geometry()
    available_geometry = screen.availableGeometry()

    window = GPTSoVITSClient(core=core, screen_geometry=screen_geometry)
    window.show()
    sys.exit(app.exec_())