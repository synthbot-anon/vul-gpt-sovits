from PyQt5.QtWidgets import (QFrame, QLineEdit, QHBoxLayout, QVBoxLayout,
    QLabel, QDialog, QPushButton, QTableView, QHeaderView, QComboBox
)
from PyQt5.QtGui import QStandardItemModel, QStandardItem
from PyQt5.QtCore import (pyqtSignal, QObject, QRunnable, QThreadPool, Qt, QSize)
from gui.core import GPTSovitsCore
from gui.stopwatch import Stopwatch
from gui.util import qshrink
# mega.py is not maintained anymore but the encryption/decryption functions
# should still work.
from mega.crypto import (base64_to_a32, base64_url_decode, decrypt_attr,
    decrypt_key, a32_to_base64, a32_to_str, get_chunks, str_to_a32)
from Crypto.Cipher import AES
from Crypto.PublicKey import RSA
from Crypto.Util import Counter
from pathlib import Path
from logging import error
from functools import partial
import os
import fnmatch
import platform
import sys
import httpx
import re
import json
import tempfile
import shutil
import time
import requests
from typing import Tuple

# https://stackoverflow.com/questions/64488709/how-can-i-list-the-contents-of-a-mega-public-folder-by-its-shared-url-using-meg
def get_nodes_in_shared_folder(root_folder: str) -> dict:
    data = [{"a": "f", "c": 1, "ca": 1, "r": 1}]
    response = httpx.post(
        "https://g.api.mega.co.nz/cs",
        params={'id': 0,  # self.sequence_num
                'n': root_folder},
        data=json.dumps(data)
    )
    json_resp = response.json()
    return json_resp[0]["f"]

def get_file_download_data(root_folder : str, file_id: str):
    data = [{"a": "g", "g": 1, "n": file_id}]
    response = httpx.post(
        "https://g.api.mega.co.nz/cs",
        params = {'id': 0, 'n': root_folder},
        data=json.dumps(data)
    )
    json_resp = response.json()
    return json_resp[0]
    # at = attributes
    # s = size of file
    # g = download link

def download_shared_file(
    shared_file_handle : str, # ^^^
    file_data : dict,
    base64_node_key : str, # the base64 node key
    dest_path=None,
    dest_filename=None):

    file_key = base64_to_a32(base64_node_key)
    k = (file_key[0] ^ file_key[4], file_key[1] ^ file_key[5],
            file_key[2] ^ file_key[6], file_key[3] ^ file_key[7])
    iv = file_key[4:6] + (0, 0)
    meta_mac = file_key[6:8]

    file_url = file_data['g']
    file_size = file_data['s']
    attribs = base64_url_decode(file_data['at'])
    attribs = decrypt_attr(attribs, k)

    if dest_filename is not None:
        file_name = dest_filename
    else:
        file_name = attribs['n']

    input_file = requests.get(file_url, stream=True).raw

    if dest_path is None:
        dest_path = ''
    else:
        dest_path += '/'

    with tempfile.NamedTemporaryFile(mode='w+b',
        prefix='megapy_',
        delete=False) as temp_output_file:
        k_str = a32_to_str(k)
        counter = Counter.new(128,
                                initial_value=((iv[0] << 32) + iv[1]) << 64)
        aes = AES.new(k_str, AES.MODE_CTR, counter=counter)

        mac_str = '\0' * 16
        mac_encryptor = AES.new(k_str, AES.MODE_CBC,
                                mac_str.encode("utf8"))
        iv_str = a32_to_str([iv[0], iv[1], iv[0], iv[1]])

        for chunk_start, chunk_size in get_chunks(file_size):
            chunk = input_file.read(chunk_size)
            chunk = aes.decrypt(chunk)
            temp_output_file.write(chunk)

            encryptor = AES.new(k_str, AES.MODE_CBC, iv_str)
            for i in range(0, len(chunk) - 16, 16):
                block = chunk[i:i + 16]
                encryptor.encrypt(block)

            # fix for files under 16 bytes failing
            if file_size > 16:
                i += 16
            else:
                i = 0

            block = chunk[i:i + 16]
            if len(block) % 16:
                block += b'\0' * (16 - (len(block) % 16))
            mac_str = mac_encryptor.encrypt(encryptor.encrypt(block))

            file_info = os.stat(temp_output_file.name)
        file_mac = str_to_a32(mac_str)
        # check mac integrity
        if (file_mac[0] ^ file_mac[1],
                file_mac[2] ^ file_mac[3]) != meta_mac:
            raise ValueError('Mismatched mac')
        output_path = Path(dest_path + file_name)
    # Move this outside the context manager
    # Otherwise Windows will fail (due to file lock)
    shutil.move(temp_output_file.name, output_path)

# file handle needs to be followed by file key

def parse_folder_url(url: str) -> Tuple[str, str]:
    "Returns (public_handle, key) if valid. If not returns None."
    REGEXP1 = re.compile(r"mega.[^/]+/folder/([0-z-_]+)#([0-z-_]+)(?:/folder/([0-z-_]+))*")
    REGEXP2 = re.compile(r"mega.[^/]+/#F!([0-z-_]+)[!#]([0-z-_]+)(?:/folder/([0-z-_]+))*")
    m = re.search(REGEXP1, url)
    if not m:
        m = re.search(REGEXP2, url)
    if not m:
        return None
    root_folder = m.group(1)
    key = m.group(2)
    return (root_folder, key)

def decrypt_node_key(key_str: str, shared_key: str) -> Tuple[int, ...]:
    encrypted_key = base64_to_a32(key_str.split(":")[1])
    return decrypt_key(encrypted_key, shared_key)

class BuildIndexWorkerEmitters(QObject):
    done = pyqtSignal()
    error = pyqtSignal(str)

class BuildIndexWorker(QRunnable):
    def __init__(self, master_file_index, master_file_url):
        super().__init__()
        self.master_file_index = master_file_index
        self.master_file_url = master_file_url
        self.emitters = BuildIndexWorkerEmitters()

    def run(self):
        t = parse_folder_url(self.master_file_url)
        if t is None:
            self.emitters.error.emit('Invalid master file URL in config')
            return
        try:
            (root_folder, shared_enc_key) = t
            nodes = get_nodes_in_shared_folder(root_folder)
            shared_key = base64_to_a32(shared_enc_key)

            records = {}
            for node in nodes:
                key = decrypt_node_key(node["k"], shared_key)
                node_key = key
                if node["t"] == 0: # Is a file
                    k = (key[0] ^ key[4], key[1] ^ key[5], key[2] ^ key[6], key[3] ^ key[7])
                elif node["t"] == 1: # Is a folder
                    k = key
                attrs = decrypt_attr(base64_url_decode(node["a"]), k)
                file_name = attrs["n"]
                file_id = node["h"]
                if file_name.endswith('.flac'):
                    # k is the node key.
                    records[file_name] = {"id": file_id, "k": a32_to_base64(node_key)} 

            with open(self.master_file_index, 'w', encoding='utf-8') as f:
                json.dump(records, f)
            print("Done")
            self.emitters.done.emit()
        except Exception as e:
            print(f"Error: {e}")
            self.emitters.error.emit(str(e))

class RefAudioDownloadWorkerEmitters(QObject):
    done = pyqtSignal()
    error = pyqtSignal(str)

class RefAudioDownloadWorker(QRunnable):
    def __init__(self,
        ref_audios_dir : str,
        master_file_url : str,
        file_id : str,
        node_key : str):
        super().__init__()
        self.ref_audios_dir = ref_audios_dir
        self.master_file_url = master_file_url
        self.file_id = file_id
        self.node_key = node_key
        self.emitters = RefAudioDownloadWorkerEmitters()

    def run(self):
        t = parse_folder_url(self.master_file_url)
        if t is None:
            self.emitters.error.emit('Invalid master file URL in config')
            return
        (root_node, _) = t
        try:
            file_data = get_file_download_data(root_node,
                file_id=self.file_id)
            download_shared_file(
                shared_file_handle=self.file_id,
                file_data=file_data,
                base64_node_key=self.node_key,
                dest_path=self.ref_audios_dir)
            self.emitters.done.emit()
        except Exception as e:
            self.emitters.error.emit(str(e))

FILE_COL = 0
DOWNLOAD_BTN_COL = 1

class MegaTableView(QTableView):
    def __init__(self, records : list, browser):
        super().__init__()

        self.visible_widgets = {}
        self.records = records
        self.browser = browser
        self.verticalScrollBar().valueChanged.connect(self.on_scroll)
        self.on_scroll()

    def sizeHint(self):
        return QSize(1000, 400)

    def create_custom_widgets(self, row):
        record = self.records[row]

        download_btn = QPushButton("Download")
        download_btn.clicked.connect(
            partial(self.browser.download_row, row))
        self.setIndexWidget(
            self.model().index(row, DOWNLOAD_BTN_COL), download_btn)
        self.visible_widgets[row] = (download_btn)

    def remove_custom_widgets(self, row):
        if row in self.visible_widgets:
            self.setIndexWidget(self.model().index(row, DOWNLOAD_BTN_COL), None)
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
        pass

    def resizeEvent(self, event):
        super().resizeEvent(event)
        self.on_scroll()

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

class MegaBrowser(QDialog):
    new_audios_downloaded = pyqtSignal()

    def __init__(self, core : GPTSovitsCore, parent=None):
        super().__init__(parent)
        self.core = core
        self.new_audios_downloaded.connect(self.core.newAudiosDownloaded)
        self.index_file = self.core.cfg.master_file_index
        self.thread_pool = QThreadPool()

        self.resize(1000, 600)

        lay1 = QVBoxLayout(self)

        self.results_view = MegaTableView([], self)
        results_frame = QFrame()
        lay4 = QVBoxLayout(results_frame)
        qshrink(lay4)
        self.lay4 = lay4
        lay1.addWidget(results_frame)

        status_frame = QFrame()
        lay3 = QHBoxLayout(status_frame)
        qshrink(lay3)
        self.status = QLabel()
        lay3.addWidget(self.status)
        self.status.setWordWrap(True)
        lay1.addWidget(status_frame)

        search_frame = QFrame()
        lay2 = QHBoxLayout(search_frame)
        search_filter = QLineEdit()
        lay2.addWidget(QLabel("Glob search"))
        lay2.addWidget(search_filter)
        # For ~70k records this is too slow to update in realtime
        search_button = QPushButton("Search")
        search_button.clicked.connect(self.build_results_view)
        lay2.addWidget(search_button)
        lay1.addWidget(search_frame)
        
        self.search_filter = search_filter

        lay2.addWidget(QLabel("Sort"))
        sort_combo = QComboBox()
        lay2.addWidget(sort_combo)
        sort_combo.addItem("")
        sort_combo.addItem("Length (asc.)")
        sort_combo.addItem("Length (desc.)")
        self.sort_combo = sort_combo
        sort_combo.currentIndexChanged.connect(self.build_results_view)

        rebuild_button = QPushButton("Rebuild master file index")
        rebuild_button.clicked.connect(self.build_index)
        self.rebuild_button = rebuild_button
        # This is a costly operation so you shouldn't be able to trigger it
        # by accidental key presses
        self.rebuild_button.setDefault(False)
        lay1.addWidget(rebuild_button)
        
        stopwatch = Stopwatch()
        self.stopwatch = stopwatch
        lay3.addWidget(self.stopwatch)
        self.rowToRecordMap = []
        self.rowToPathMap = []
        self.index = {}
        if not Path(self.index_file).exists():
            self.build_index()
        else:
            self.build_results_view()

    def build_results_view(self, force_reload=False):
        model = QStandardItemModel()
        model : QStandardItemModel
        model.setHorizontalHeaderLabels(["File", "Download"])
        self.results_view : MegaTableView
        self.results_view.deleteLater()
        t1 = time.perf_counter()
        if not Path(self.index_file).exists():
            self.results_view.setModel(model)
            return
        try:
            if (not len(self.index)) or force_reload:
                with open(self.index_file, 'r', encoding='utf-8') as f:
                    self.index = json.load(f)
            index = self.index
        except Exception as e:
            print(e)
            self.status.setText(f"Error: {e}")
        self.rowToRecordMap.clear()
        self.rowToPathMap.clear()
        i : int = 0

        t2 = time.perf_counter()
        file_names : list = [k for k in index.keys()]

        sort = self.sort_combo.currentText()
        if len(sort):
            if sort == "Length (asc.)":
                file_names.sort(key=lambda n: len(n))
            elif sort == "Length (desc.)":
                file_names.sort(key=lambda n: len(n), reverse=True)
        
        if len(self.search_filter.text()):
            file_names = fnmatch.filter(file_names, self.search_filter.text())
        t3 = time.perf_counter()

        for file_name in file_names:
            record = index[file_name]
            item = QStandardItem(file_name)
            item : QStandardItem
            item.setData(record, Qt.UserRole) # file id and node key
            model.appendRow(item)
            self.rowToRecordMap.append(record)
            self.rowToPathMap.append(file_name)
            i += 1
        t4 = time.perf_counter()
        self.data = index
        self.results_view = MegaTableView(self.rowToPathMap, self)
        self.results_view.setModel(model)
        self.results_view.horizontalHeader().setSectionResizeMode(
            FILE_COL, QHeaderView.Stretch)
        self.lay4.addWidget(self.results_view)

        # print(f'load: {t2 - t1:.2f} s')
        # print(f'filter: {t3 - t2:.2f} s')
        # print(f'widget: {t4 - t3:.2f} s')

    def download_row(self, row):
        row : int
        record : dict = self.rowToRecordMap[row]
        file_id : str = record['id']
        base64_node_key : str = record['k']
        name = self.rowToPathMap[row]
        worker = RefAudioDownloadWorker(
            self.core.cfg.ref_audios_dir,
            self.core.cfg.master_file_url,
            file_id, base64_node_key)
        self.status.setText(f"Downloading file {name}")
        def handle_error(e: str, name : str):
            error(e)
            self.status.setText(f"Failed to download file {name}")
        worker.emitters.error.connect(
            partial(handle_error, name=name))
        def handle_done(name : str):
            self.status.setText(f"Finished downloading file {name}")
            self.new_audios_downloaded.emit()
        worker.emitters.done.connect(
            partial(handle_done, name=name))
        self.thread_pool.start(worker)

    def build_index(self):
        worker = BuildIndexWorker(
            self.index_file,
            self.core.cfg.master_file_url)
        self.status.setText("Building master file index (this can take a while)...")
        def handle_error(e: str):
            error(e)
            self.rebuild_button.setEnabled(False)
            self.stopwatch.stop_reset_stopwatch()
            self.status.setText(f"Error: {e}")
        worker.emitters.error.connect(handle_error)
        def handle_done():
            self.rebuild_button.setEnabled(True)
            self.stopwatch.stop_reset_stopwatch()
            self.status.setText(
                f"Finished building master file index to {self.index_file}")
            self.build_results_view(True)
        worker.emitters.done.connect(handle_done)
        self.stopwatch.stop_reset_stopwatch()
        self.stopwatch.start_stopwatch()
        self.thread_pool.start(worker)