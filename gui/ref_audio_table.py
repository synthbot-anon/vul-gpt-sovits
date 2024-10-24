from PyQt5.QtCore import QAbstractTableModel, Qt, QModelIndex
from PyQt5.QtWidgets import QTableView, QCheckBox
from gui.database import RefAudio
from gui.audio_preview import AudioPreviewWidget
from functools import partial

class AudioTableModel(QAbstractTableModel):
    def __init__(self,
        ras : list[RefAudio],
        hashesCheckedSet : set[str]):
        super().__init__()
        self.ras = ras
        self.hashesCheckedSet = hashesCheckedSet
        self.headers = ['Filepath', 'Character', 'Utterance', 'Hash', 'Select',
            'Play']

    def rowCount(self, parent=None):
        return len(self.ras)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole:
            ra = self.ras[index.row()]
            if index.column() == 0: # Filepath
                return ra.local_filepath
            if index.column() == 1: # Character
                return ra.character
            if index.column() == 2: # Utterance
                return ra.utterance
            if index.column() == 3: # Audio hash (first 7 chars)
                return ra.audio_hash[:7]
        return None

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.headers[section]
            if orientation == Qt.Vertical:
                return None # Don't show side indices

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        # Items in columns 0 (Filepath), 3 (Audio Hash), and 4 (Checkbox) are non-editable
        if index.column() in (0, 3):  # Column indices for non-editable items
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled  # Non-editable items

        if index.column() == 4:  # Checkbox (column 4)
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable  # Checkbox items

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable  # Editable items


class AudioTableView(QTableView):
    def __init__(self, 
        model : AudioTableModel, 
        ras : list[RefAudio],
        hashesCheckedSet : set[str]):
        super().__init__()
        self.setModel(model)
        self.ras = ras
        self.hashesCheckedSet = hashesCheckedSet

        self.visible_widgets = {}

        self.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.on_scroll()

    def create_custom_widgets(self, row):
        ra = self.ras[row]

        check_box = QCheckBox()
        if ra.audio_hash in self.hashesCheckedSet:
            check_box.setChecked(True)
        check_box.stateChanged.connect(
            partial(self.update_hashes_set, 
            check_box=check_box, audio_hash=ra.audio_hash)
        )
        self.setIndexWidget(self.model().index(row, 4), check_box)

        preview_button = AudioPreviewWidget(button_only=True,
            drag_enabled=False, pausable=False)
        preview_button.from_file(ra.local_filepath)
        self.setIndexWidget(self.model().index(row, 5), preview_button)

        self.visible_widgets[row] = (check_box, preview_button)

    def remove_custom_widgets(self, row):
        if row in self.visible_widgets:
            self.setIndexWidget(self.model().index(row, 4), None)
            self.setIndexWidget(self.model().index(row, 5), None)
            del self.visible_widgets[row]

    def on_scroll(self):
        """Handler for scroll events, responsible for creating/removing widgets based on visibility."""
        # Get the visible rows
        visible_rows = self.get_visible_rows()

        # Add custom widgets for newly visible rows
        for row in visible_rows:
            if row not in self.visible_widgets:
                self.create_custom_widgets(row)

        # Remove custom widgets for rows that are no longer visible
        for row in list(self.visible_widgets.keys()):
            if row not in visible_rows:
                self.remove_custom_widgets(row)

    def get_visible_rows(self):
        """Determine which rows are currently visible in the viewport."""
        index_top = self.indexAt(self.rect().topLeft())  # Get the top visible index
        index_bottom = self.indexAt(self.rect().bottomLeft())  # Get the bottom visible index

        if not index_top.isValid():
            return []
        
        top_row = index_top.row()
        bottom_row = index_bottom.row()

        # Ensure we cover the full range of visible rows
        if bottom_row == -1:
            bottom_row = self.model().rowCount() - 1

        return range(top_row, bottom_row + 1)

    def update_hashes_set(self, 
        check_box: QCheckBox,
        audio_hash: str):
        if check_box.isChecked():
            self.hashesCheckedSet.add(audio_hash)
        else:
            self.hashesCheckedSet.discard(audio_hash)