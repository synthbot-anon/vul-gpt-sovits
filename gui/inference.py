from PyQt5.QtWidgets import (
    QPushButton, QFrame, QLineEdit, QLabel, QGroupBox,
    QPlainTextEdit, QVBoxLayout, QHBoxLayout, QComboBox,
    QGridLayout, QCheckBox, QScrollArea
)
from gui.core import GPTSovitsCore
from gui.util import qshrink
from gui.audio_preview import RichAudioPreviewWidget

class InferenceFrame(QGroupBox):
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


        # inputs_grid
        inputs_f = QFrame()
        lay1.addWidget(inputs_f)
        inputs_grid = QGridLayout(inputs_f)
        qshrink(inputs_grid, 4)

        # TODO validators for below

        # input prompt language
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

        # use reference audio
        useref_f = QFrame()
        useref_f_lay = QHBoxLayout(useref_f)
        qshrink(useref_f_lay)
        inputs_grid.addWidget(useref_f, 2, 1)
        useref_f_lay.addWidget(QLabel("Use ref. audio"))
        self.useref_cb = QCheckBox()
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
        qresize(self.topk_f_edit)
        topk_f_lay.addWidget(self.topk_f_edit)

        inputs_grid.addWidget(topk_f, 0, 0)

        # top_p
        topp_f = QFrame()
        topp_f_lay = QHBoxLayout(topp_f)
        qshrink(topp_f_lay)
        topp_f_lay.addWidget(QLabel("Top p"))
        self.topp_f_edit = QLineEdit(str(cfg.top_p))
        qresize(self.topp_f_edit)
        topp_f_lay.addWidget(self.topp_f_edit)

        inputs_grid.addWidget(topp_f, 1, 0)

        # temp
        temp_f = QFrame()
        temp_f_lay = QHBoxLayout(temp_f)
        qshrink(temp_f_lay)
        temp_f_lay.addWidget(QLabel("Temperature"))
        self.temp_f_edit = QLineEdit(str(cfg.temperature))
        qresize(self.temp_f_edit)
        temp_f_lay.addWidget(self.temp_f_edit)

        inputs_grid.addWidget(temp_f, 2, 0)

        # rep_penalty
        repp_f = QFrame()
        repp_f_lay = QHBoxLayout(repp_f)
        qshrink(repp_f_lay)
        repp_f_lay.addWidget(QLabel("Repetition penalty"))
        self.repp_f_edit = QLineEdit(str(cfg.repetition_penalty))
        qresize(self.repp_f_edit)
        repp_f_lay.addWidget(self.repp_f_edit)

        inputs_grid.addWidget(repp_f, 3, 0)

        # batch_size
        bs_f = QFrame()
        bs_f_lay = QHBoxLayout(bs_f)
        qshrink(bs_f_lay)
        bs_f_lay.addWidget(QLabel("Batch size"))
        self.bs_f_edit = QLineEdit(str(cfg.batch_size))
        qresize(self.bs_f_edit)
        bs_f_lay.addWidget(self.bs_f_edit)

        inputs_grid.addWidget(bs_f, 0, 2)

        # sentence delay
        send_f = QFrame()
        send_f_lay = QHBoxLayout(send_f)
        qshrink(send_f_lay)
        send_f_lay.addWidget(QLabel("Add pause (s)"))
        self.send_f_edit = QLineEdit(str(cfg.fragment_interval))
        qresize(self.send_f_edit)
        send_f_lay.addWidget(self.send_f_edit)

        inputs_grid.addWidget(send_f, 1, 2)

        # speed factor
        spd_f = QFrame()
        spd_f_lay = QHBoxLayout(spd_f)
        qshrink(spd_f_lay)
        spd_f_lay.addWidget(QLabel("Speed factor"))
        self.spd_f_edit = QLineEdit(str(cfg.speed_factor))
        qresize(self.spd_f_edit)
        spd_f_lay.addWidget(self.spd_f_edit)

        inputs_grid.addWidget(spd_f, 2, 2)

        # seed
        sd_f = QFrame()
        sd_f_lay = QHBoxLayout(sd_f)
        qshrink(sd_f_lay)
        sd_f_lay.addWidget(QLabel("Seed"))
        self.sd_f_edit = QLineEdit()
        qresize(self.sd_f_edit)
        sd_f_lay.addWidget(self.sd_f_edit)

        inputs_grid.addWidget(sd_f, 3, 2)

        # keep_random
        kpr_f = QFrame()
        kpr_f_lay = QHBoxLayout(kpr_f)
        qshrink(kpr_f_lay)
        kpr_f_lay.addWidget(QLabel("Use random"))
        self.kpr_cb = QCheckBox()
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
        self.n_f_edit = QLineEdit()
        qresize(self.n_f_edit)
        nr_f_lay.addWidget(self.n_f_edit)

        inputs_grid.addWidget(nr_f, 5, 2)

        # generate
        self.gen_button = QPushButton("Generate")
        self.gen_button.setEnabled(False)
        self.gen_button.setFixedHeight(60)
        inputs_grid.addWidget(self.gen_button, 4, 0, 3, 2)

        self.core = core
        self.core.hostReady.connect(
            lambda ready: self.gen_button.setEnabled(ready))

        # generations
        gen_box = QGroupBox("Generations")
        gen_box.setStyleSheet("QGroupBox { font: normal; }")
        self.gen_lay = QVBoxLayout(gen_box)
        scroll = QScrollArea()
        scroll.setWidget(gen_box)
        scroll.setWidgetResizable(True)
        lay1.addWidget(scroll)

        self.preview_widgets = []

        self.build_preview_widgets()

    def set_text_split_by_code(self, code : str):
        if len(code) < 4:
            return
        c = int(code[3])
        self.text_split.setCurrentIndex(c)

    def build_preview_widgets(self, n_generations: int =3):
        self.preview_widgets : list
        for widg in self.preview_widgets:
            widg.deleteLater()
        self.preview_widgets.clear()

        for n in range(n_generations):
            preview_widget = RichAudioPreviewWidget()
            preview_widget.from_file(r"C:\Users\vul\Downloads\gptsovits_bundle2\sovits5\rvc1.mp3")
            self.gen_lay.addWidget(preview_widget)
            self.preview_widgets.append(preview_widget)