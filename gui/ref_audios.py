from PyQt5.QtWidgets import (
    QGroupBox, QVBoxLayout, QTableWidget, QTableWidgetItem,
    QHeaderView, QCheckBox, QPushButton)
from PyQt5.QtCore import pyqtSignal, Qt, QSize
from gui.core import GPTSovitsCore
from gui.database import GPTSovitsDatabase, CLIENT_DB_FILE, RefAudio
from gui.util import ppp_parse, AUDIO_EXTENSIONS
from gui.audio_preview import AudioPreviewWidget
from pathlib import Path
from functools import partial
import soundfile as sf
import hashlib
import os

class RefAudiosContext:
    def __init__(self, core : GPTSovitsCore):
        self.core = core
        self.database = GPTSovitsDatabase(db_file=CLIENT_DB_FILE)
        
        self.autoload_from_dir()
        
    def autoload_from_dir(self):
        cfg = self.core.cfg
        os.makedirs(cfg['ref_audios_dir'], exist_ok=True)
        ref_audios_dir = Path(cfg['ref_audios_dir'])
        for path in ref_audios_dir.rglob('*'):
            if path.suffix.lower() in AUDIO_EXTENSIONS:
                path = path.absolute()
                self.add_ref_audio(path)

    def get_ref_audios(self):
        return self.database.list_ref_audio()
    
    def __len__(self):
        return RefAudio.select().count()
    
    def add_ref_audio(
        self,
        local_filepath: Path):
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
                
        # Append to end of list
        self.database.update_with_ref_audio(
            audio_hash=sha256_hash.hexdigest(),
            local_filepath=str(local_filepath),
            character=character,
            utterance=utterance,
            list_position=len(self))

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
        
    # this won't handle uploading; that only happens once we actually
    # need to send TTS requests
    # or will it? maybe it's better to passively upload reference audios in
    # idle time?

class RefAudiosFrame(QGroupBox):
    shouldBuildTable = pyqtSignal()
    def __init__(self, core : GPTSovitsCore):
        super().__init__(title="Reference Audios")
        self.context = RefAudiosContext(core)
        self.lay = QVBoxLayout(self)
        self.table = None
        
        self.hashesCheckedSet : set[str] = set()
        
        self.shouldBuildTable.connect(self.build_table)
        
        # pb = QPushButton("Rebuild table")
        # pb.clicked.connect(self.shouldBuildTable)
        # self.lay.addWidget(pb)

        self.shouldBuildTable.emit()
        
    def updateHashesCheckedSet(self, 
        check_box: QCheckBox,
        audio_hash: str):
        if check_box.isChecked():
            self.hashesCheckedSet.add(audio_hash)
        else:
            self.hashesCheckedSet.remove(audio_hash)
        
    def build_table(self):
        if isinstance(self.table, QTableWidget):
            self.table.deleteLater()
            del self.table
        self.table = QTableWidget()
        table_cols = [
            'Filepath', 'Character', 'Utterance', 'Hash', 'Select', 'Play']

        self.table.setColumnCount(len(table_cols))
        self.table.setHorizontalHeaderLabels(table_cols)
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

        ras : list[RefAudio] = self.context.get_ref_audios()
        ras.sort(key=lambda ra:
            (ra.list_position if ra.list_position is not None else 0))
        self.table.setRowCount(len(ras))
        for i,ra in enumerate(ras):
            ra : RefAudio
            self.table.setItem(
                i, 0, QTableWidgetItem(ra.local_filepath))
            self.table.setItem(
                i, 1, QTableWidgetItem(ra.character))
            self.table.setItem(
                i, 2, QTableWidgetItem(ra.utterance))
            hash_item = QTableWidgetItem(ra.audio_hash[:7])
            self.table.setItem(
                i, 3, hash_item)
            check_box = QCheckBox()
            if ra.audio_hash in self.hashesCheckedSet:
                check_box.setChecked(True)
            check_box.stateChanged.connect(
                partial(self.updateHashesCheckedSet,
                check_box = check_box,
                audio_hash = ra.audio_hash)
            )
            self.table.setCellWidget(i, 4, check_box)
            preview_button = AudioPreviewWidget(
                button_only=True, drag_enabled=False, pausable=False)
            preview_button.from_file(ra.local_filepath)
            self.table.setCellWidget(i, 5, preview_button)
            
        self.lay.addWidget(self.table)
        
    # TODO: Manipulation buttons:
    # Add from file (drag and drop)
    # Delete
    # You should be able to edit the character and text inplace
    # You should also get a search/filter for utterance/character