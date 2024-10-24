from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QTableView,
    QHeaderView, QCheckBox, QPushButton, QFrame, QHBoxLayout,
    QLabel, QLineEdit, QComboBox)
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from gui.core import GPTSovitsCore
from gui.database import GPTSovitsDatabase, CLIENT_DB_FILE, RefAudio
from gui.util import ppp_parse, AUDIO_EXTENSIONS
from gui.audio_preview import AudioPreviewWidget
from gui.file_button import FileButton
from gui.ref_audio_table import AudioTableModel, AudioTableView
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

class RefAudiosContext:
    def __init__(self, core : GPTSovitsCore):
        self.core = core
        self.database = GPTSovitsDatabase(db_file=CLIENT_DB_FILE)
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
        with open(local_filepath, 'rb') as audio_file:
            for byte_block in iter(lambda: audio_file.read(4096), b""):
                sha256_hash.update(byte_block)
                
        # If this is a PPP-style audio name,
        # we can try roughly parsing it for extra data
        ppp_meta = ppp_parse(str(local_filepath))
        character = None 
        utterance = None
        if ppp_meta is not None:
            character = ppp_meta['char']
            utterance = ppp_meta['transcr']
            
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
        
    # this won't handle uploading; that only happens once we actually
    # need to send TTS requests
    # or will it? maybe it's better to passively upload reference audios in
    # idle time?

class RefAudiosFrame(QGroupBox):
    # signal(character filter, fuzzy text filter)
    shouldBuildTable = pyqtSignal()
    def __init__(self, core : GPTSovitsCore):
        super().__init__(title="Reference Audios")
        self.context = RefAudiosContext(core)
        self.lay = QVBoxLayout(self)
        self.table = None
        
        self.hashesCheckedSet : set[str] = set()
        self.rowToHashMap = dict()
        self.hashToPathMap = dict()
        
        self.shouldBuildTable.connect(self.build_table)
        
        #pb = QPushButton("Rebuild table")
        #pb.clicked.connect(self.shouldBuildTable)
        #self.lay.addWidget(pb)
        
        bf = QFrame()
        bflay = QHBoxLayout(bf)

        self.add_ref_button = FileButton(
            label="Add reference audio",
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
        
        bf2 = QFrame()
        bflay = QHBoxLayout(bf2)
        bflay.addWidget(QLabel("Filter by character"))
        cf = QFrame()
        self.cflay = QVBoxLayout(cf)
        bflay.addWidget(cf)
        bflay.addWidget(QLabel("Filter by utterance"))
        self.utterance_edit = QLineEdit()
        self.utterance_edit.editingFinished.connect(
            self.shouldBuildTable)
        bflay.addWidget(self.utterance_edit)

        tbf = QFrame()
        self.tbflay = QVBoxLayout(tbf)
        self.lay.addWidget(tbf)
        self.lay.addWidget(bf)
        self.lay.addWidget(bf2)

        self.build_character_filter()
        self.build_table()

    # TODO this needs to be triggered after edits
    def build_character_filter(self):
        self.ras = self.context.get_ref_audios()
        character_filters = set()
        for ra in self.ras:
            if ra.character is not None:
                character_filters.add(ra.character)

        if (hasattr(self, 'character_filter_cb') and 
            isinstance(self.character_filter_cb, QComboBox)):
            self.character_filter_cb : QComboBox
            self.character_filter_cb.deleteLater()
            del self.character_filter_cb

        self.character_filter_cb = QComboBox()
        # Representing no filter
        self.character_filter_cb.addItem('')
        character_filters = list(character_filters)
        character_filters.sort()
        for character in character_filters:
            self.character_filter_cb.addItem(character)

        self.character_filter_cb.currentIndexChanged.connect(
            self.shouldBuildTable
        )
        self.cflay.addWidget(self.character_filter_cb)

    def delete_selected_rows(self, b):
        for row in self.get_selected_rows():
            ra = self.context.get_ref_audio(self.rowToHashMap[row])
            ra.is_deleted = True
            ra.save()
        self.shouldBuildTable.emit()
        
    def get_selected_rows(
        self):
        self.table : AudioTableView
        selection_model = self.table.selectionModel()
        selected_indexes = selection_model.selectedIndexes()
        selected_rows = {index.row() for index in selected_indexes}
        return selected_rows
        
    def update_hashes_set(self, 
        check_box: QCheckBox,
        audio_hash: str):
        if check_box.isChecked():
            self.hashesCheckedSet.add(audio_hash)
        else:
            self.hashesCheckedSet.discard(audio_hash)
            
    def add_selected_ref_audios(self, 
        ras : list[str]):
        if not len(ras):
            return
        for ra in ras:
            ra : str
            self.context.add_ref_audio(Path(ra), do_override_delete=True)
        self.shouldBuildTable.emit()

    def fuzzy_utterance_filter(self, ras : list[RefAudio]):
        query = self.utterance_edit.text().strip()
        if len(query) == 0:
            return ras
        ra : RefAudio
        print(f"Performing fuzzy filter for {query}")
        by_utterance = {ra.utterance : ra for ra in ras}
        utterances = [k for k in by_utterance.keys()]
        matches = process.extract(query, utterances,
            scorer=fuzz.WRatio, score_cutoff=50)
        return [by_utterance[match[0]] for match in matches]

    def filter_by_characters(self, ras : list[RefAudio]):
        self.character_filter_cb : QComboBox
        character_choice = str(self.character_filter_cb.currentText())
        if not len(character_choice):
            return ras
        else:
            return [ra for ra in ras if ra.character == character_choice]
        
    def build_table(self):
        ras : list[RefAudio] = self.context.get_ref_audios()

        # Filter deleted files
        ras = [ra for ra in ras if not ra.is_deleted]

        # Apply character filter
        ras = self.filter_by_characters(ras)

        # Apply text filter
        ras = self.fuzzy_utterance_filter(ras)

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

        model = AudioTableModel(ras, self.hashesCheckedSet)
        self.table = AudioTableView(model, ras, self.hashesCheckedSet)
        self.table.setSelectionBehavior(QTableView.SelectRows)
        self.table.setSelectionMode(QTableView.ExtendedSelection)

        self.table.setMinimumWidth(900)
        self.table.setMinimumHeight(400)
        
        self.table.setColumnWidth(0, 80)
        self.table.setColumnWidth(1, 120)
        self.table.setColumnWidth(3, 120)
        self.table.setColumnWidth(4, 60)
        self.table.setColumnWidth(5, 60)
        
        self.table.horizontalHeader().setSectionResizeMode(0,
            QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(1,
            QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(2,
            QHeaderView.Stretch)
        self.table.horizontalHeader().setSectionResizeMode(3,
            QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(4,
            QHeaderView.Fixed)
        self.table.horizontalHeader().setSectionResizeMode(5,
            QHeaderView.Fixed)
        
        for i,ra in enumerate(ras):
            self.rowToHashMap[i] = ra.audio_hash

        self.table.selectionModel().selectionChanged.connect(
            lambda: self.delete_button.setText(
                f"Delete highlighted rows ({len(self.get_selected_rows())})"))
        self.tbflay.addWidget(self.table)
        et = time.perf_counter()
        
    # TODO: Manipulation buttons:
    # You should be able to edit the character and text inplace
    # But not the file path or hash
    # TODO: Search buttons
    # You should also get a search/filter for utterance/character