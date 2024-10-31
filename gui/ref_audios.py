from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QTableView,
    QHeaderView, QCheckBox, QPushButton, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QComboBox)
from PyQt5.QtCore import pyqtSignal, Qt, QSize, QObject
from gui.core import GPTSovitsCore
from gui.database import GPTSovitsDatabase, CLIENT_DB_FILE, RefAudio
from gui.util import ppp_parse, AUDIO_EXTENSIONS, qshrink
from gui.audio_preview import AudioPreviewWidget
from gui.file_button import FileButton
from gui.ref_audio_table import (AudioTableModel, AudioTableView,
    FILEPATH_COL, CHARACTER_COL, EMOTION_COL, UTTERANCE_COL,
    AUDIOHASH_COL, PRIMARY_CHECKBOX_COL, AUX_CHECKBOX_COL,
     PREVIEW_COL, DURATION_COL)
from pathlib import Path
from functools import partial
from typing import Optional
from rapidfuzz import process, fuzz
import logging
from logging import info, basicConfig, debug
import soundfile as sf
import hashlib
import os
import time

#logging.basicConfig(
#    level = logging.DEBUG
#)

class RefAudiosContext(QObject):
    newAudiosDownloaded = pyqtSignal()
    def __init__(self, core : GPTSovitsCore):
        super().__init__()
        self.core = core
        self.database = core.database
        def new_audios_downloaded():
            self.autoload_from_dir()
            self.database.integrity_update()
            self.newAudiosDownloaded.emit()
            # ra : RefAudio
            # print([ra.utterance for ra in self.database.list_ref_audio()])
        self.core.newAudiosDownloaded.connect(new_audios_downloaded)
        self.autoload_from_dir()
        
    def autoload_from_dir(self):
        cfg = self.core.cfg
        os.makedirs(cfg['ref_audios_dir'], exist_ok=True)
        ref_audios_dir = Path(cfg['ref_audios_dir'])
        i = len(self)
        for path in ref_audios_dir.rglob('*'):
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                path = path.absolute()
                self.add_ref_audio(path, override_list_position=i)
                i = i + 1

    def get_ref_audios(self):
        return self.database.list_ref_audio()

    def get_ref_audio(self, audio_hash : str):
        return self.database.get_ref_audio(audio_hash)
    
    def __len__(self):
        return RefAudio.select().count()
    
    def add_ref_audio(
        self,
        local_filepath: Path,
        override_list_position: Optional[int] = None,
        do_override_delete = None):
        assert local_filepath.exists()
        
        sha256_hash = hashlib.sha256()

        audio, sr = sf.read(local_filepath)
        duration_seconds = len(audio) / sr

        with open(local_filepath, 'rb') as audio_file:
            for byte_block in iter(lambda: audio_file.read(4096), b""):
                sha256_hash.update(byte_block)

        # If this is a PPP-style audio name,
        # we can try roughly parsing it for extra data
        ppp_meta = ppp_parse(str(local_filepath))
        character = None 
        utterance = None
        emotion = None
        if ppp_meta is not None:
            character = ppp_meta['char']
            utterance = ppp_meta['transcr']
            emotion = ppp_meta['emotion']
            
        list_position = None
        if override_list_position is not None:
            list_position = list_position
        else:
            list_position = len(self)
                
        # Append to end of list
        override_delete = None
        if do_override_delete == True:
            override_delete = False
        self.database.update_with_ref_audio(
            audio_hash=sha256_hash.hexdigest(),
            local_filepath=str(local_filepath),
            character=character,
            utterance=utterance,
            emotion=emotion,
            duration=duration_seconds,
            list_position=list_position,
            override_delete=override_delete)

    def update_ref_audio(
        self,
        audio_hash: str,
        local_filepath: str = None,
        utterance: str = None,
        character: str = None):
        ref_audio = self.database.get_ref_audio(
            audio_hash)
        if local_filepath is not None:
            ref_audio.local_filepath = utterance
        if utterance is not None:
            ref_audio.utterance = utterance
        if character is not None:
            ref_audio.character = character
        ref_audio.save()
        
class RefAudiosFrame(QGroupBox):
    # signal(character filter, fuzzy text filter)
    shouldBuildTable = pyqtSignal()
    def __init__(self, core : GPTSovitsCore,
        compact_mode : bool = True):
        super().__init__(title="Reference Audios")
        self.compact_mode = compact_mode
        self.setStyleSheet("QGroupBox { font: bold; }")
        def new_audios_downloaded():
            self.shouldBuildTable.emit()
            self.build_character_filter()
        self.context = RefAudiosContext(core)
        self.context.newAudiosDownloaded.connect(new_audios_downloaded)
        self.lay = QVBoxLayout(self)
        self.table = None
        
        self.auxSelectedSet : set[str] = core.auxSelectedSet
        self.primaryRefHash : set[str] = core.primaryRefHash
        self.rowToHashMap = dict()
        self.hashToPathMap = dict()
        
        self.shouldBuildTable.connect(self.build_table)
        
        #pb = QPushButton("Rebuild table")
        #pb.clicked.connect(self.shouldBuildTable)
        #self.lay.addWidget(pb)
        
        bf = QFrame()
        bflay = QHBoxLayout(bf)
        qshrink(bflay)

        self.add_ref_button = FileButton(
            label="Add reference audio (or drag here)",
            dialog_filter = "All Audio Files (*.wav *.mp3 *.ogg *.flac *.aac)"
        )
        bflay.addWidget(self.add_ref_button)
        self.add_ref_button.filesSelected.connect(
            self.add_selected_ref_audios            
        )
        self.delete_button = QPushButton("Delete highlighted rows (0)")
        self.delete_button.clicked.connect(
            self.delete_selected_rows
        )
        bflay.addWidget(self.delete_button)

        self.deselect_button = QPushButton("Deselect all")
        self.deselect_button.clicked.connect(self.deselect)
        bflay.addWidget(self.deselect_button)
        
        bf2 = QFrame()
        bflay = QHBoxLayout(bf2)
        qshrink(bflay)
        bflay.addWidget(QLabel("Filter by character"))
        cf = QFrame()
        self.cflay = QVBoxLayout(cf)
        qshrink(self.cflay)
        bflay.addWidget(cf)
        ef = QFrame()
        self.emotion_edit = QLineEdit()
        self.emotion_edit.editingFinished.connect(self.shouldBuildTable)
        bflay.addWidget(QLabel("Filter by emotion (comma separated)"))
        bflay.addWidget(self.emotion_edit)

        bf3 = QFrame()
        bf3lay = QHBoxLayout(bf3)
        qshrink(bf3lay)
        bf3lay.addWidget(QLabel("Filter by utterance"))
        self.utterance_edit = QLineEdit()
        self.utterance_edit.editingFinished.connect(
            self.shouldBuildTable)
        bf3lay.addWidget(self.utterance_edit)

        bf4 = QFrame()
        bf4lay = QHBoxLayout(bf4)
        qshrink(bf4lay)

        self.primary_display = QLabel("Primary selected audio: ")
        # self.primary_display.setFixedWidth(600)
        self.primary_display.setWordWrap(True)
        bf4lay.addWidget(self.primary_display)
        self.show_select = QCheckBox("Show only selected")
        bf4lay.addWidget(self.show_select)
        self.show_select.stateChanged.connect(self.shouldBuildTable)

        tbf = QFrame()
        self.tbflay = QVBoxLayout(tbf)
        self.lay.addWidget(tbf)
        self.lay.addWidget(bf)
        self.lay.addWidget(bf2)
        self.lay.addWidget(bf3)
        self.lay.addWidget(bf4)

        self.sumdur = QLabel("Sum of durations: 0.0")
        self.sumdur.setWordWrap(True)
        self.lay.addWidget(self.sumdur)

        core.databaseSelfUpdate.connect(self.shouldBuildTable)

        self.build_character_filter()
        self.build_table()

    def build_character_filter(self):
        self.ras = self.context.get_ref_audios()
        character_filters = set()
        for ra in self.ras:
            if ra.character is not None and not ra.is_deleted:
                character_filters.add(ra.character)

        old_selection : str = ''
        if not hasattr(self, 'character_filter_cb'):
            self.character_filter_cb = QComboBox()
        else:
            old_selection = self.character_filter_cb.currentText()
        self.character_filter_cb.clear()
        # Representing no filter
        self.character_filter_cb.addItem('')
        character_filters = list(character_filters)
        character_filters.sort()
        for character in character_filters:
            self.character_filter_cb.addItem(character)

        old_idx = self.character_filter_cb.findText(
            old_selection)
        if old_idx != -1:
            self.character_filter_cb.setCurrentIndex(old_idx)

        self.character_filter_cb.currentIndexChanged.connect(
            self.shouldBuildTable
        )
        self.cflay.addWidget(self.character_filter_cb)

    def delete_selected_rows(self, b):
        for row in self.get_selected_rows():
            ra = self.context.get_ref_audio(self.rowToHashMap[row])
            ra.is_deleted = True
            ra.save()
        self.build_character_filter()
        self.shouldBuildTable.emit()

    def deselect(self, b):
        self.context.core.primaryRefHash.clear()
        self.context.core.auxSelectedSet.clear()
        self.shouldBuildTable.emit()
        self.update_hashes_checked()
        
    def get_selected_rows(
        self):
        self.table : AudioTableView
        selection_model = self.table.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        selected_rows = {index.row() for index in selected_indexes}
        return selected_rows
        
    def add_selected_ref_audios(self, 
        ras : list[str]):
        if not len(ras):
            return
        for ra in ras:
            ra : str
            self.context.add_ref_audio(Path(ra), do_override_delete=True)
        self.build_character_filter()
        self.shouldBuildTable.emit()

    def fuzzy_utterance_filter(self, ras : list[RefAudio]):
        query = self.utterance_edit.text().strip()
        if len(query) == 0:
            return ras
        ra : RefAudio
        #print(f"Performing fuzzy filter for {query}")
        by_utterance = {ra.utterance : ra for ra in ras}
        utterances = [k for k in by_utterance.keys()]
        matches = process.extract(query, utterances,
            scorer=fuzz.WRatio, score_cutoff=60)
        return [by_utterance[match[0]] for match in matches]

    def filter_by_characters(self, ras : list[RefAudio]):
        self.character_filter_cb : QComboBox
        character_choice = str(self.character_filter_cb.currentText())
        if not len(character_choice):
            return ras
        else:
            return [ra for ra in ras if ra.character == character_choice]

    def filter_by_emotions(self,
        ras : list[RefAudio]):
        emotion_filter = self.emotion_edit.text()
        if not len(emotion_filter):
            return ras
        emotions = [s.strip().lower() for s in emotion_filter.split(',')]
        return [ra for ra in ras if all(
            emot in (ra.emotion.lower() if ra.emotion is not None else '')
            for emot in emotions)]
    
    def update_hashes_checked(self):
        ra : RefAudio
        primaryRefAudio = [
            ra for ra in self.ras if ra.audio_hash in self.primaryRefHash]
        if len(primaryRefAudio):
            self.primary_display.setText(
                f"Primary selected audio: "
                f"{primaryRefAudio[0].local_filepath}")
        else:
            self.primary_display.setText(
                f"Primary selected audio: ")

        if len(primaryRefAudio):
            sumdur = primaryRefAudio[0].duration
            if sumdur < 3:
                text = f"Duration: {sumdur:.2f} s (< 3). Warning - Short reference audio can have adverse effects on character resemblance and audio quality"
                self.sumdur.setText(text)
            elif sumdur > 10:
                text = f"Duration: {sumdur:.2f} s (> 10). Warning - Long reference audio can have adverse effects on pronunciation and memory usage"
                self.sumdur.setText(text)
            else:
                text = f"Duration: {sumdur:.2f} s"
                self.sumdur.setText(text)
        else:
            text = f"Duration: {0.0} s"
            self.sumdur.setText(text)
        
    def build_table(self):
        ras : list[RefAudio] = self.context.get_ref_audios()

        # Filter deleted files
        ras = [ra for ra in ras if not ra.is_deleted]

        # Check for selection if show only selected
        if self.show_select.isChecked():
            ras = [ra for ra in ras if ra.audio_hash 
                in self.context.core.auxSelectedSet or
                ra.audio_hash in self.context.core.primaryRefHash]

        # Apply text filter
        ras = self.fuzzy_utterance_filter(ras)

        # Apply character filter
        ras = self.filter_by_characters(ras)

        # Apply emotion filter
        ras = self.filter_by_emotions(ras)

        # Most recent files should appear at top
        ras.sort(reverse=True, 
            key=lambda ra:
            (ra.list_position if ra.list_position is not None else 0))

        st = time.perf_counter()
        self.hashToPathMap = {
            ra.audio_hash : ra.local_filepath for ra in ras
        }
        self.rowToHashMap.clear()

        if hasattr(self, 'table') and isinstance(self.table, AudioTableView):
            self.table : AudioTableView
            self.table.deleteLater()
            del self.table

        # data modification logic is in AudioTableModel
        model = AudioTableModel(ras)
        model.dataHasChanged.connect(self.build_character_filter)
        self.table = AudioTableView(model, ras, self.auxSelectedSet,
            self.primaryRefHash)
        self.table.hashesCheckedChanged.connect(self.update_hashes_checked)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)

        self.table.setMinimumHeight(200)
        
        if self.compact_mode:
            self.table.setColumnWidth(FILEPATH_COL, 40)
            self.table.setColumnWidth(CHARACTER_COL, 80)
            self.table.setColumnWidth(EMOTION_COL, 80)
            self.table.setColumnWidth(DURATION_COL, 80)
            self.table.setColumnWidth(UTTERANCE_COL, 120)
            self.table.setColumnWidth(AUDIOHASH_COL, 60)
            self.table.setColumnWidth(PRIMARY_CHECKBOX_COL, 60)
            self.table.setColumnWidth(AUX_CHECKBOX_COL, 40)
            self.table.setColumnWidth(PREVIEW_COL, 60)
        else:
            self.table.setColumnWidth(FILEPATH_COL, 80)
            self.table.setColumnWidth(CHARACTER_COL, 100)
            self.table.setColumnWidth(EMOTION_COL, 100)
            self.table.setColumnWidth(DURATION_COL, 80)
            self.table.setColumnWidth(UTTERANCE_COL, 180)
            self.table.setColumnWidth(AUDIOHASH_COL, 60)
            self.table.setColumnWidth(PRIMARY_CHECKBOX_COL, 80)
            self.table.setColumnWidth(AUX_CHECKBOX_COL, 40)
            self.table.setColumnWidth(PREVIEW_COL, 60)
        
        self.table.horizontalHeader().setSectionResizeMode(FILEPATH_COL,
            QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(CHARACTER_COL,
            QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(EMOTION_COL,
            QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(DURATION_COL,
            QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(UTTERANCE_COL,
            QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(AUDIOHASH_COL,
            QHeaderView.Interactive)
        self.table.horizontalHeader().setSectionResizeMode(PRIMARY_CHECKBOX_COL,
            QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(AUX_CHECKBOX_COL,
            QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(PREVIEW_COL,
            QHeaderView.Stretch)
        #self.table.horizontalHeader().setStretchLastSection(True)

        for i,ra in enumerate(ras):
            self.rowToHashMap[i] = ra.audio_hash

        self.table.selectionModel().selectionChanged.connect(
            lambda: self.delete_button.setText(
                f"Delete highlighted rows ({len(self.get_selected_rows())})"))
        self.tbflay.addWidget(self.table)
        et = time.perf_counter()
        
    # TODO: Manipulation
    # You should be able to edit the character and text inplace
    # But not the file path or hash