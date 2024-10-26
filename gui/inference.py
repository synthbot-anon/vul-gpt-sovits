from PyQt5.QtWidgets import (
    QPushButton, QFrame, QLineEdit, QLabel, QGroupBox,
    QPlainTextEdit, QVBoxLayout, QHBoxLayout, QComboBox,
    QGridLayout, QCheckBox, QScrollArea
)
from PyQt5.QtCore import (
    pyqtSignal, QObject, QRunnable, QThreadPool
)
from PyQt5.QtGui import (
    QIntValidator, QDoubleValidator
)
from gui.core import GPTSovitsCore
from gui.util import qshrink, sanitize_filename, get_available_filename
from gui.audio_preview import RichAudioPreviewWidget
from gui.database import RefAudio
from gui.requests import PostWorker
from gui.stopwatch import Stopwatch
from pathlib import Path
from logging import error
import soundfile as sf
import httpx
import base64
import numpy as np
import json
import sys
import os

class InferenceWorkerEmitter(QObject):
    # Returns info, an index and a single audio array of int
    inferenceOutput = pyqtSignal(dict, int, list)
    sr = pyqtSignal(int)
    statusUpdate = pyqtSignal(str)
    error = pyqtSignal()

class InferenceWorker(QRunnable):
    def __init__(self, 
        host : str,
        is_local : bool,
        info : dict,
        hash_to_path_map : dict):
        super().__init__()
        self.info = info
        self.host = host
        self.is_local = is_local
        self.hash_to_path_map = hash_to_path_map
        self.emitters = InferenceWorkerEmitter()

    def run(self):
        info = self.info
        # 1. Test server for reference audio hashes
        url = f"{self.host}/test_hashes"

        selected_hashes : list
        selected_hashes = [info['ref_audio_hash']]
        if info.get('aux_ref_audio_hashes') is not None:
            selected_hashes.extend(info['aux_ref_audio_hashes'])
        try:
            response = httpx.post(url, json={'hashes': selected_hashes})
            if response.status_code == 200:
                self.emitters.statusUpdate.emit('Testing audio hashes')
            else:
                self.emitters.statusUpdate.emit(f'Failed test audio hashes')
                self.emitters.error.emit()
                return
        except httpx.RequestError as e:
            error(f"Error testing audio hashes: {e}")
            self.emitters.statusUpdate.emit(f'Error testing audio hashes: {e}')
            self.emitters.error.emit()
            return

        hashes_known : dict[str, bool] = response.json()
        unknown_hashes = [k for k,v in hashes_known.items() if not v]
        self.emitters.statusUpdate.emit('Finished testing audio hashes')

        # 2. Upload reference audios it doesn't know about
        for unknown_hash in unknown_hashes:
            self.upload_from_hash(unknown_hash)

        # 3. Send the inference request
        chunks = []
        self.sentences = []
        self.repetitions = []
        self.is_parallelized = False
        self.repetition_ctr = 0
        self.emitters.statusUpdate.emit('Beginning generation')
        try:
            infer_url = f"{self.host}/generate"
            with httpx.stream("POST", infer_url, json=self.info, timeout=None) as r:
                for line in r.iter_lines():
                    if line is None or not line.strip(): # skip empty lines
                        continue
                    chunk = json.loads(line)
                    self.process_chunk(chunk) # will transmit non-parallelized
        except httpx.RequestError as e:
            self.emitters.statusUpdate.emit(str(e))
            self.emitters.error.emit()
            return

        # 4. (Transmitting parallel inference).         
        # We count the number of individual sentences and divide it by
        # n_repetitions, then split the list of output sentences
        # into n_repetitions to get audio we can concatenate back into our
        # final outputs.
        try:
            if self.is_parallelized:
                segment_size = len(self.sentences) // info['n_repetitions']
                segments = [
                    self.sentences[i:i+segment_size] for i in range(
                        0, len(self.sentences), segment_size)]
                assert len(segments) == info['n_repetitions']
                for i,segment in enumerate(segments):
                    segment: list(np.ndarray)
                    segment_audio : np.ndarray = np.concatenate(
                        segment, dtype=np.int16)
                    self.emitters.inferenceOutput.emit(
                        self.info,
                        i,
                        segment_audio.tolist())
        except Exception as e:
            self.emitters.statusUpdate.emit(str(e))
            self.emitters.error.emit()
            return

        # Since we control the gui_server source this shouldn't create 
        # compatibility issues since there is no other way for this request
        # to go through.

    def process_chunk(self, chunk):
        if 'warning' in chunk:
            self.emitters.statusUpdate.emit(f'Warning: {chunk["warning"]}')
            return # No-op

        audio = chunk['audio']
        audio : bytes = base64.b64decode(audio.encode('ascii'))
        audio_array : np.ndarray = np.frombuffer(audio, dtype=np.int16)
        sr = chunk['sr']
        self.emitters.sr.emit(sr)

        # Then this generation can be split into sentences
        if chunk['parallelized']:
            # To construct the final output, we take each chunk and split it
            # into its individual sentences using 'audio' and 'this_gen_lengths'.
            sentence_lengths = chunk['this_gen_lengths']
            start = 0
            for length in sentence_lengths:
                end = start + length
                self.sentences.append(audio_array[start:end])
                start = end
            self.is_parallelized = True
        else:
            self.emitters.inferenceOutput.emit(
                self.info,
                self.repetition_ctr,
                audio_array.tolist())
            self.repetition_ctr += 1


    def upload_from_hash(self, hsh):
        upload_url = f"{self.host}/post_ref_audio"
        pth = self.hash_to_path_map[hsh]
        with open(pth, 'rb') as f:
            audio = f.read()
        upload_data = {
            'audio_hash': hsh,
        }
        if self.is_local:
            upload_data['local_filepath'] = pth
        else:
            base64_audio_data = base64.b64encode(audio).decode("ascii")
            upload_data['base64_audio_data'] = base64_audio_data
        try:
            self.emitters.statusUpdate.emit(f'Uploading {pth}')
            response = httpx.post(upload_url, json=upload_data, timeout=None)
            if response.status_code == 201:
                self.emitters.statusUpdate.emit(f'Uploaded {pth}')
            else:
                self.emitters.statusUpdate.emit(f'Failed upload {pth}')
        except httpx.RequestError as e:
            error(f"Error uploading ref audio: {e}")
            raise

class InferenceFrame(QGroupBox):
    resultsReady = pyqtSignal(bool)
    def __init__(self, core : GPTSovitsCore):
        super().__init__(title="Inference")
        self.setStyleSheet("QGroupBox { font: bold; }")
        self.interactable_group = []

        cfg = core.cfg['inference']

        lay1 = QVBoxLayout(self)

        # Reference audio selection is in the reference audio frame
        # But may bear repeating here?

        pe_box = QGroupBox("Text prompt")
        pe_box.setStyleSheet("QGroupBox { font: normal; }")
        lay1.addWidget(pe_box)
        pelay = QVBoxLayout(pe_box)
        self.prompt_edit = QPlainTextEdit()
        self.prompt_edit.setMinimumWidth(300)
        pelay.addWidget(self.prompt_edit)


        # inputs grid
        inputs_f = QFrame()
        lay1.addWidget(inputs_f)
        inputs_grid = QGridLayout(inputs_f)
        qshrink(inputs_grid, 4)

        # text_lang
        prompt_lang_f = QFrame()
        prompt_lang_f_lay = QHBoxLayout(prompt_lang_f)
        qshrink(prompt_lang_f_lay)
        prompt_lang = QComboBox()
        prompt_lang.addItem(
            "English", userData="en")
        prompt_lang.addItem(
            "Mandarin", userData="all_zh")
        prompt_lang.addItem(
            "Cantonese (Yue)", userData="all_yue")
        prompt_lang.addItem(
            "Japanese", userData="all_ja")
        prompt_lang.addItem(
            "Korean", userData="all_ko")
        prompt_lang_f_lay.addWidget(QLabel("Prompt language"))
        prompt_lang_f_lay.addWidget(prompt_lang)
        inputs_grid.addWidget(prompt_lang_f, 0, 1)
        self.prompt_lang = prompt_lang

        # prompt_lang
        ref_lang_f = QFrame()
        ref_lang_f_lay = QHBoxLayout(ref_lang_f)
        qshrink(ref_lang_f_lay)
        ref_lang = QComboBox()
        ref_lang.addItem(
            "English", userData="en")
        ref_lang.addItem(
            "Mandarin", userData="all_zh")
        ref_lang.addItem(
            "Cantonese (Yue)", userData="all_yue")
        ref_lang.addItem(
            "Japanese", userData="all_ja")
        ref_lang.addItem(
            "Korean", userData="all_ko")
        ref_lang_f_lay.addWidget(QLabel("Ref. audio language"))
        ref_lang_f_lay.addWidget(ref_lang)
        inputs_grid.addWidget(ref_lang_f, 1, 1)
        self.ref_lang = ref_lang

        # use reference audio
        # TODO - I'm not sure this parameter actually has any effect
        useref_f = QFrame()
        useref_f_lay = QHBoxLayout(useref_f)
        qshrink(useref_f_lay)
        inputs_grid.addWidget(useref_f, 2, 1)
        useref_f_lay.addWidget(QLabel("Use ref. audio"))
        self.useref_cb = QCheckBox() 
        self.useref_cb.setChecked(True)
        self.useref_cb.setEnabled(False)
        useref_f_lay.addWidget(self.useref_cb)

        # text_split_method
        text_split_f = QFrame()
        text_split_f_lay = QHBoxLayout(text_split_f)
        qshrink(text_split_f_lay)
        text_split = QComboBox()
        text_split.addItem(
            "Do not batch", userData="cut0")
        text_split.addItem(
            "Batch every 4 sentences", userData="cut1")
        text_split.addItem(
            "Batch every 50 chars", userData="cut2")
        text_split.addItem(
            "Batch by Chinese punctuation", userData="cut3")
        text_split.addItem(
            "Batch by English punctuation", userData="cut4")
        text_split.addItem(
            "Batch by all punctuation", userData="cut5")
        text_split_f_lay.addWidget(QLabel("Text split"))
        text_split_f_lay.addWidget(text_split)
        inputs_grid.addWidget(text_split_f, 3, 1)
        self.text_split = text_split
        self.set_text_split_by_code(cfg.text_split_method)

        def qresize(widg):
            widg.setFixedWidth(60)

        # top_k
        topk_f = QFrame()
        topk_f_lay = QHBoxLayout(topk_f)
        qshrink(topk_f_lay)
        topk_f_lay.addWidget(QLabel("Top k"))
        self.topk_f_edit = QLineEdit(str(cfg.top_k))
        top_k_validator = QIntValidator(1, 100)
        self.topk_f_edit.setValidator(top_k_validator)
        qresize(self.topk_f_edit)
        topk_f_lay.addWidget(self.topk_f_edit)

        inputs_grid.addWidget(topk_f, 0, 0)

        # top_p
        topp_f = QFrame()
        topp_f_lay = QHBoxLayout(topp_f)
        qshrink(topp_f_lay)
        topp_f_lay.addWidget(QLabel("Top p"))
        self.topp_f_edit = QLineEdit(str(cfg.top_p))
        top_p_validator = QDoubleValidator(0, 1, 2)
        self.topp_f_edit.setValidator(top_p_validator)
        qresize(self.topp_f_edit)
        topp_f_lay.addWidget(self.topp_f_edit)

        inputs_grid.addWidget(topp_f, 1, 0)

        # temp
        temp_f = QFrame()
        temp_f_lay = QHBoxLayout(temp_f)
        qshrink(temp_f_lay)
        temp_f_lay.addWidget(QLabel("Temperature"))
        self.temp_f_edit = QLineEdit(str(cfg.temperature))
        temp_f_validator = QDoubleValidator(0, 2, 2)
        self.temp_f_edit.setValidator(temp_f_validator)
        qresize(self.temp_f_edit)
        temp_f_lay.addWidget(self.temp_f_edit)

        inputs_grid.addWidget(temp_f, 2, 0)

        # rep_penalty
        repp_f = QFrame()
        repp_f_lay = QHBoxLayout(repp_f)
        qshrink(repp_f_lay)
        repp_f_lay.addWidget(QLabel("Repetition penalty"))
        self.repp_f_edit = QLineEdit(str(cfg.repetition_penalty))
        repp_f_validator = QDoubleValidator(0.0, 2.0, 2)
        self.repp_f_edit.setValidator(repp_f_validator)
        qresize(self.repp_f_edit)
        repp_f_lay.addWidget(self.repp_f_edit)

        inputs_grid.addWidget(repp_f, 3, 0)

        # batch_size
        bs_f = QFrame()
        bs_f_lay = QHBoxLayout(bs_f)
        qshrink(bs_f_lay)
        bs_f_lay.addWidget(QLabel("Batch size"))
        self.bs_f_edit = QLineEdit(str(cfg.batch_size))
        bs_f_validator = QIntValidator(1, cfg.max_batch_size)
        self.bs_f_edit.setValidator(bs_f_validator)
        qresize(self.bs_f_edit)
        bs_f_lay.addWidget(self.bs_f_edit)

        inputs_grid.addWidget(bs_f, 0, 2)

        # sentence delay
        send_f = QFrame()
        send_f_lay = QHBoxLayout(send_f)
        qshrink(send_f_lay)
        send_f_lay.addWidget(QLabel("Add pause (s)"))
        self.send_f_edit = QLineEdit(str(cfg.fragment_interval))
        send_f_validator = QDoubleValidator(0.01, 1.0, 2)
        self.send_f_edit.setValidator(send_f_validator)
        qresize(self.send_f_edit)
        send_f_lay.addWidget(self.send_f_edit)

        inputs_grid.addWidget(send_f, 1, 2)

        # speed factor
        spd_f = QFrame()
        spd_f_lay = QHBoxLayout(spd_f)
        qshrink(spd_f_lay)
        spd_f_lay.addWidget(QLabel("Speed factor"))
        self.spd_f_edit = QLineEdit(str(cfg.speed_factor))
        spd_f_validator = QDoubleValidator(0.6, 1.65, 2)
        self.spd_f_edit.setValidator(spd_f_validator)
        qresize(self.spd_f_edit)
        spd_f_lay.addWidget(self.spd_f_edit)

        inputs_grid.addWidget(spd_f, 2, 2)

        # seed
        sd_f = QFrame()
        sd_f_lay = QHBoxLayout(sd_f)
        qshrink(sd_f_lay)
        sd_f_lay.addWidget(QLabel("Seed"))
        self.sd_f_edit = QLineEdit()
        sd_f_validator = QIntValidator()
        self.sd_f_edit.setValidator(sd_f_validator)
        qresize(self.sd_f_edit)
        sd_f_lay.addWidget(self.sd_f_edit)

        inputs_grid.addWidget(sd_f, 3, 2)

        # keep_random
        kpr_f = QFrame()
        kpr_f_lay = QHBoxLayout(kpr_f)
        qshrink(kpr_f_lay)
        kpr_f_lay.addWidget(QLabel("Randomize seed"))
        self.kpr_cb = QCheckBox()
        self.kpr_cb.setChecked(cfg.use_random)
        def update_seed_field():
            self.sd_f_edit.setEnabled(not self.kpr_cb.isChecked())
        self.kpr_cb.stateChanged.connect(
            update_seed_field
            # If randomize seed is enabled, then the seed field
            # should be disabled.
        )
        update_seed_field()
        kpr_f_lay.addWidget(self.kpr_cb)

        inputs_grid.addWidget(kpr_f, 4, 2)

        # cache results
        # ch_f = QFrame()
        # ch_f_lay = QHBoxLayout(ch_f)
        # qshrink(ch_f_lay)
        # ch_f_lay.addWidget(QLabel("Cache results"))
        # self.ch_cb = QCheckBox()
        # ch_f_lay.addWidget(self.ch_cb)

        # inputs_grid.addWidget(ch_f, 6, 2)

        # n_reps
        nr_f = QFrame()
        nr_f_lay = QHBoxLayout(nr_f)
        qshrink(nr_f_lay)
        nr_f_lay.addWidget(QLabel("Repetitions"))
        self.n_f_edit = QLineEdit(str(cfg.n_repetitions))
        n_f_validator = QIntValidator(1, 10)
        self.n_f_edit.setValidator(n_f_validator)
        qresize(self.n_f_edit)
        nr_f_lay.addWidget(self.n_f_edit)

        inputs_grid.addWidget(nr_f, 5, 2)

        # generate
        self.gen_button = QPushButton("Generate")
        self.gen_button.setEnabled(False)
        self.gen_button.clicked.connect(self.generate)
        inputs_grid.addWidget(self.gen_button, 4, 0, 1, 1)

        self.core = core

        # interrupt
        self.interrupt_button = QPushButton("Interrupt")
        self.interrupt_button.setEnabled(False)
        self.interrupt_button.clicked.connect(self.interrupt)
        inputs_grid.addWidget(self.interrupt_button, 4, 1, 1, 1)

        self.core.hostReady.connect(self.set_ready)
        self.core.modelsReady.connect(self.set_ready)
        
        def generation_set_ready(ready: bool):
            self.gen_button.setEnabled(ready)
        self.resultsReady.connect(generation_set_ready)

        # status
        stf = QFrame()
        stl = QHBoxLayout(stf)
        qshrink(stl)
        self.status_label = QLabel("Status")
        self.status_label.setFixedWidth(400)
        self.stopwatch = Stopwatch()
        stl.addWidget(self.status_label)
        stl.addWidget(self.stopwatch)

        def update_stopwatch(ready: bool):
            if not ready: # Starting connection
                # Reset stopwatch
                self.stopwatch.stop_reset_stopwatch()
                self.stopwatch.start_stopwatch()
            else:
                # Stop stopwatch
                self.stopwatch.stop_reset_stopwatch()
        self.resultsReady.connect(update_stopwatch)

        inputs_grid.addWidget(stf, 5, 0, 1, 2)

        # generations
        gen_box = QGroupBox("Generations")
        gen_box.setStyleSheet("QGroupBox { font: normal; }")
        self.gen_lay = QVBoxLayout(gen_box)
        scroll = QScrollArea()
        scroll.setWidget(gen_box)
        scroll.setWidgetResizable(True)
        lay1.addWidget(scroll)

        self.preview_widgets = []
        self.thread_pool = QThreadPool()
        self.sr = 0

    def set_ready(self, ready : bool):
        self.gen_button.setEnabled(ready)
        self.interrupt_button.setEnabled(ready)

    def set_text_split_by_code(self, code : str):
        if len(code) < 4:
            return
        c = int(code[3])
        self.text_split.setCurrentIndex(c)

    def clear_preview_widgets(self):
        for widg in self.preview_widgets:
            widg.deleteLater()
        self.preview_widgets.clear()

    def warn(self, msg: str):
        self.status_label.setText(msg)
        pass

    def interrupt(self):
        post_worker = PostWorker(
            self.core.host, '/stop', None)
        self.thread_pool.start(post_worker)

    def handle_inference_output(self, info : dict, idx : int, audio : list):
        # We don't expect these to be sent out of order, so we can
        # ignore idx
        sr = self.sr

        # Write output to disk
        utterance = info['text']
        characters : str = info['characters']
        output_fn = sanitize_filename(
            characters+'_'+utterance, max_length=50) + '.flac'
        output_path = Path(self.core.cfg.outputs_dir) / output_fn
        final_fn = get_available_filename(str(output_path))
        if not Path(self.core.cfg.outputs_dir).exists():
            os.makedirs(self.core.cfg.outputs_dir, exist_ok=True)
        audio = np.array(audio, dtype=np.int16)
        sf.write(final_fn, audio, sr)

        # create preview widget
        preview_widget = RichAudioPreviewWidget()
        preview_widget.from_file(final_fn)
        self.gen_lay.addWidget(preview_widget)
        self.preview_widgets.append(preview_widget)

        if idx >= (info['n_repetitions'] - 1):
            self.resultsReady.emit(True)

    def generate(self):
        info = {
            'text': str(self.prompt_edit.toPlainText()),
            'text_lang': self.prompt_lang.currentData(),
            'prompt_lang': self.ref_lang.currentData(),
            'top_k': int(self.topk_f_edit.text()),
            'top_p': float(self.topp_f_edit.text()),
            'temperature': float(self.temp_f_edit.text()),
            'text_split_method': self.text_split.currentData(),
            'batch_size': int(self.bs_f_edit.text()),
            'speed_factor': float(self.spd_f_edit.text()),
            'fragment_interval': float(self.send_f_edit.text()),
            'repetition_penalty': float(self.repp_f_edit.text()),
            'keep_random': self.kpr_cb.isChecked(),
            'n_repetitions': int(self.n_f_edit.text())
        }
        if not len(self.core.primaryRefHash):
            self.warn("Warning: A primary reference audio is required."
                " Not inferring.")
            return

        if not len(self.prompt_edit.toPlainText()):
            self.warn("Warning: Cannot infer an empty prompt.")
            return

        primaryRefHash = list(self.core.primaryRefHash)[0]
        aux_hashes = [h for h in self.core.auxSelectedSet]
        aux_hashes.sort()
        ra : RefAudio = self.core.database.get_ref_audio(primaryRefHash)
        aux_ras = {h: self.core.database.get_ref_audio(h) for h in aux_hashes}

        info['ref_audio_hash'] = primaryRefHash
        if len(self.sd_f_edit.text()):
            info['seed'] = int(self.sd_f_edit.text())

        if len(aux_hashes):
            info['aux_ref_audio_hashes'] = aux_hashes

        info['prompt_text'] = ra.utterance
        info['characters'] = ra.character

        r: RefAudio
        hash_to_path_map = {
            h: r.local_filepath for h,r in aux_ras.items()
        }
        hash_to_path_map[primaryRefHash] = ra.local_filepath
        self.warn("Sent generation request")
        self.resultsReady.emit(False)
        worker = InferenceWorker(
            host=self.core.host,
            is_local=self.core.is_local,
            info=info,
            hash_to_path_map=hash_to_path_map)
        worker.emitters.statusUpdate.connect(self.warn)
        worker.emitters.inferenceOutput.connect(self.handle_inference_output)
        worker.emitters.sr.connect(self.set_sr)
        def handle_error():
            # Allow retries
            self.stopwatch.stop_reset_stopwatch()
            self.gen_button.setEnabled(True)
        worker.emitters.error.connect(handle_error)
        self.clear_preview_widgets()
        self.thread_pool.start(worker)

    def set_sr(self, sr : int):
        self.sr = sr