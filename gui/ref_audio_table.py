from PyQt5.QtCore import (
    QAbstractTableModel, Qt, QModelIndex, QThreadPool, pyqtSignal)
from PyQt5.QtWidgets import (
    QTableView, QCheckBox, QLabel, QStyledItemDelegate, QWidget,
    QAbstractItemDelegate, QRadioButton)
from gui.database import RefAudio
from gui.audio_preview import SmallAudioPreviewWidget
from functools import partial
from logging import debug
import time

FILEPATH_COL = 0
CHARACTER_COL = 1
EMOTION_COL = 2
DURATION_COL = 3
UTTERANCE_COL = 4
AUDIOHASH_COL = 5
PRIMARY_CHECKBOX_COL = 6
AUX_CHECKBOX_COL = 7
PREVIEW_COL = 8

class CustomDelegate(QStyledItemDelegate):
    # Signal to notify when editing is finished
    editingFinished = pyqtSignal(QWidget)

    def __init__(self, parent=None):
        super().__init__(parent)
        super().closeEditor.connect(lambda ed, hint:
            self.editingFinished.emit(ed))

class AudioTableModel(QAbstractTableModel):
    dataHasChanged = pyqtSignal()
    def __init__(self,
        ras : list[RefAudio]):
        super().__init__()
        self.ras = ras
        self.headers = ['Filepath', 'Character', 'Emotion', 'Duration',
            'Utterance', 'Hash', 'Primary', 'Aux', 'Play']

    def rowCount(self, parent=None):
        return len(self.ras)

    def columnCount(self, parent=None):
        return len(self.headers)

    def data(self, index, role=Qt.DisplayRole):
        if role == Qt.DisplayRole or role == Qt.EditRole:
            ra = self.ras[index.row()]
            if index.column() == FILEPATH_COL: # Filepath
                return ra.local_filepath
            if index.column() == CHARACTER_COL: # Character
                return ra.character
            if index.column() == EMOTION_COL: # Emotion
                return ra.emotion
            if index.column() == DURATION_COL: # Duration
                return f"{ra.duration:.2f}"
            if index.column() == UTTERANCE_COL: # Utterance
                return ra.utterance
            if index.column() == AUDIOHASH_COL: # Audio hash 
                return ra.audio_hash
        elif role == Qt.ToolTipRole:
            ra = self.ras[index.row()]
            if index.column() == AUDIOHASH_COL:
                return ra.audio_hash
        return None

    def setData(self, index, value, role=Qt.EditRole):
        if role == Qt.EditRole:
            ra = self.ras[index.row()]
            if index.column() == CHARACTER_COL:
                ra.character = value
                ra.save()
                self.dataHasChanged.emit()
                return True
            if index.column() == EMOTION_COL:
                ra.emotion = value
                ra.save()
                self.dataHasChanged.emit()
                return True
            if index.column() == UTTERANCE_COL:
                ra.utterance = value
                ra.save()
                self.dataHasChanged.emit()
                return True
        return False

    def event(self, event):
        # if event.type() == event.MouseMove:
        #     index = self.indexAt(event.pos())
        #     if index.isValid() and index.column() == AUDIOHASH_COL:
        #         value = self.model().data(index, Qt.ToolTipRole)
        #         if value:
        #             self.setToolTip(str(value))
        #         else:
        #             self.setToolTip("")
        #     else:
        #         self.setToolTip("")
        return super().event(event)

    def headerData(self, section, orientation, role):
        if role == Qt.DisplayRole:
            if orientation == Qt.Horizontal:
                return self.headers[section]
            if orientation == Qt.Vertical:
                return None # Don't show side indices

    def flags(self, index: QModelIndex):
        if not index.isValid():
            return Qt.NoItemFlags

        if index.column() in (FILEPATH_COL, AUDIOHASH_COL):  # Column indices for non-editable items
            # Even though these are flagged editable,
            # The underlying modification logic is in setData - not actually editable
            return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable

        if index.column() in (PRIMARY_CHECKBOX_COL, AUX_CHECKBOX_COL):  # Checkbox 
            return Qt.ItemIsUserCheckable | Qt.ItemIsEnabled | Qt.ItemIsSelectable  # Checkbox items

        return Qt.ItemIsSelectable | Qt.ItemIsEnabled | Qt.ItemIsEditable  # Editable items


class AudioTableView(QTableView):
    hashesCheckedChanged = pyqtSignal()
    def __init__(self, 
        model : AudioTableModel, 
        ras : list[RefAudio],
        auxSelectedSet : set[str],
        primaryRefHash : set[str]):
        super().__init__()
        self.setModel(model)
        self.ras = ras
        self.auxSelectedSet = auxSelectedSet
        self.primaryRefHash = primaryRefHash

        self.visible_widgets = {}

        delegate = CustomDelegate(self)
        self.setItemDelegate(delegate)
        # delegate.editingFinished.connect(lambda w: print(w.text()))

        self.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.thread_pool = QThreadPool()
        self.on_scroll()

    def create_custom_widgets(self, row):
        ra = self.ras[row]

        check_box = QCheckBox()
        if ra.audio_hash in self.auxSelectedSet:
            check_box.setChecked(True)
        check_box.stateChanged.connect(
            partial(self.update_hashes_set, 
            check_box=check_box, audio_hash=ra.audio_hash)
        )
        self.setIndexWidget(self.model().index(row, AUX_CHECKBOX_COL), check_box)

        radio_button = QRadioButton()
        if ra.audio_hash in self.primaryRefHash:
            radio_button.setChecked(True)
        def update_primary_hash(state : bool, audio_hash : str):
            if ra.audio_hash in self.primaryRefHash and state == False:
                self.primaryRefHash.discard(audio_hash)
            elif ra.audio_hash not in self.primaryRefHash and state == True:
                self.primaryRefHash.clear()
                self.primaryRefHash.add(audio_hash)
        radio_button.toggled.connect(partial(
            update_primary_hash, audio_hash = ra.audio_hash))
        self.setIndexWidget(self.model().index(row, PRIMARY_CHECKBOX_COL), radio_button)

        preview = SmallAudioPreviewWidget(
            ra.local_filepath)
        self.setIndexWidget(self.model().index(row, PREVIEW_COL), preview)

        self.visible_widgets[row] = (check_box, preview)

    def remove_custom_widgets(self, row):
        if row in self.visible_widgets:
            self.setIndexWidget(self.model().index(row, PRIMARY_CHECKBOX_COL), None)
            self.setIndexWidget(self.model().index(row, PREVIEW_COL), None)
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
            self.auxSelectedSet.add(audio_hash)
        else:
            self.auxSelectedSet.discard(audio_hash)
        self.hashesCheckedChanged.emit()