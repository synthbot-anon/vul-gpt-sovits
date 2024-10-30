from PyQt5.QtCore import QObject, pyqtSignal, QThreadPool
from gui.default_config import default_config, DEFAULT_CONFIG_PATH
from omegaconf import OmegaConf
from gui.database import GPTSovitsDatabase, CLIENT_DB_FILE, RefAudio
from pathlib import Path
from typing import Optional
import huggingface_hub
import os
import torch
import nltk
import logging
import sys

# sys path
now_dir = os.getcwd()
sys.path.append(now_dir)
sys.path.append(f"{now_dir}/GPT_SoVITS")

from TTS_infer_pack.TTS import TTS, TTS_Config

if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

# logging
logging.getLogger("markdown_it").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("charset_normalizer").setLevel(logging.ERROR)
logging.getLogger("torchaudio._extension").setLevel(logging.ERROR)

class GPTSovitsCore(QObject):
    modelsReady = pyqtSignal(bool)
    databaseSelfUpdate = pyqtSignal()
    newModelsAvailable = pyqtSignal()

    def __init__(self):
        super().__init__()
        self.download_pretrained_models_if_not_present()

        self.thread_pool = QThreadPool()
        if not Path(DEFAULT_CONFIG_PATH).exists():
            self.cfg = OmegaConf.create(default_config)
        else:
            self.cfg = OmegaConf.load(DEFAULT_CONFIG_PATH)
        self.write_config()
        self.database = GPTSovitsDatabase(db_file=CLIENT_DB_FILE)
        self.tts_config, self.tts_pipeline = self.init_pipeline()

        self.auxSelectedSet = set()
        self.primaryRefHash = set()
        self.integrity_update()

    def check_resource(resource_name):
        try:
            print(f"Checking for resource {resource_name}")
            # Try loading the resource
            nltk.data.find(f'taggers/{resource_name}')
            return True
        except LookupError:
            # If not found, return False
            return False

    def download_pretrained_models_if_not_present(self):
        repo_id = "lj1995/GPT-SoVITS"
        local_dir = "GPT_SoVITS/pretrained_models"
        if not GPTSovitsCore.check_resource('averaged_perceptron_tagger'):
            nltk.download('averaged_perceptron_tagger')
        if not GPTSovitsCore.check_resource('averaged_perceptron_tagger_eng'):
            nltk.download('averaged_perceptron_tagger_eng')
        if not os.path.exists("GPT_SoVITS/pretrained_models/chinese-hubert-base"):
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="chinese-hubert-base/config.json", local_dir=local_dir)
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="chinese-hubert-base/preprocessor_config.json", local_dir=local_dir)
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="chinese-hubert-base/pytorch_model.bin", local_dir=local_dir)
        if not os.path.exists("GPT_SoVITS/pretrained_models/chinese-robert-wwm-ext-large"):
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="chinese-roberta-wwm-ext-large/config.json", local_dir=local_dir)
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="chinese-roberta-wwm-ext-large/tokenizer.json", local_dir=local_dir)
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="chinese-roberta-wwm-ext-large/pytorch_model.bin", local_dir=local_dir)
        if (not os.path.exists("GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt") or
            not os.path.exists("GPT_SoVITS/pretrained_models/gsv-v2final-pretrained/s2G2333k.pth")):
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="gsv-v2final-pretrained/s1bert25hz-5kh-longer-epoch=12-step=369668.ckpt", local_dir=local_dir)
            huggingface_hub.hf_hub_download(repo_id=repo_id, filename="gsv-v2final-pretrained/s2G2333k.pth", local_dir=local_dir)

    def init_pipeline(self):
        is_half = eval(os.environ.get("is_half", "True")) and torch.cuda.is_available()
        gpt_path = os.environ.get("gpt_path", None)
        sovits_path = os.environ.get("sovits_path", None)
        cnhubert_base_path = os.environ.get("cnhubert_base_path", None)
        bert_path = os.environ.get("bert_path", None)
        version=os.environ.get("version","v2")

        tts_config = TTS_Config("GPT_SoVITS/configs/tts_infer.yaml")
        tts_config.device = device
        tts_config.is_half = is_half
        tts_config.version = version
        if gpt_path is not None:
            tts_config.t2s_weights_path = gpt_path
        if sovits_path is not None:
            tts_config.vits_weights_path = sovits_path
        if cnhubert_base_path is not None:
            tts_config.cnhuhbert_base_path = cnhubert_base_path
        if bert_path is not None:
            tts_config.bert_base_path = bert_path

        tts_pipeline = TTS(tts_config)
        return tts_config, tts_pipeline

    def write_config(self):
        with open(DEFAULT_CONFIG_PATH, 'w') as f:
            f.write(OmegaConf.to_yaml(self.cfg))

    def integrity_update(self):
        if (self.database.integrity_update()):
            self.databaseSelfUpdate.emit()