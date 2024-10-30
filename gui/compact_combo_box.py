from PyQt5.QtWidgets import QApplication, QComboBox, QWidget, QVBoxLayout
from PyQt5.QtCore import QSize

class CompactComboBox(QComboBox):
    def __init__(self, width):
        super().__init__()
        self._width = width
        # Add items to combo box
        self.addItems(["Short", "A bit longer", "This is a very long item"])

    def minimumSizeHint(self):
        # Set the minimum visible size for the combo box
        return QSize(self._width, super().sizeHint().height())  

    def showPopup(self):
        # Calculate the maximum width of the items in the dropdown
        width = max(
            self.view().sizeHintForColumn(0) + self.view().verticalScrollBar().sizeHint().width(), self.width())
        self.view().setMinimumWidth(width)
        super().showPopup()