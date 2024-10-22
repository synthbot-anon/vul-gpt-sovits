from fastapi import FastAPI
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os, re, logging
import sys
import torch
import json
from pathlib import Path

# sys path
now_dir = os.getcwd()
sys.path.append(now_dir)
sys.path.append(f"{now_dir}/GPT_SoVITS")

# logging
logging.getLogger("markdown_it").setLevel(logging.ERROR)
logging.getLogger("urllib3").setLevel(logging.ERROR)
logging.getLogger("httpcore").setLevel(logging.ERROR)
logging.getLogger("httpx").setLevel(logging.ERROR)
logging.getLogger("asyncio").setLevel(logging.ERROR)
logging.getLogger("charset_normalizer").setLevel(logging.ERROR)
logging.getLogger("torchaudio._extension").setLevel(logging.ERROR)

from TTS_infer_pack.TTS import TTS, TTS_Config
from TTS_infer_pack.text_segmentation_method import get_method

# device
if torch.cuda.is_available():
    device = "cuda"
else:
    device = "cpu"

def init_pipeline():
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

app = FastAPI()
tts_config, tts_pipeline = init_pipeline()

class SetModelsInfo(BaseModel):
    gpt_path: Optional[str] = None
    sovits_path: Optional[str] = None
    cnhubert_base_path: Optional[str] = None
    bert_path: Optional[str] = None
    
from gui import model_utils
@app.post("/find_models")
def find_models():
    return model_utils.find_models(
        Path(now_dir),
        Path(now_dir) / "models",)

@app.post("/set_models")
def set_models(info: SetModelsInfo):
    # Environment variables will be used for model setup
    if (info.gpt_path is not None):
        os.environ['gpt_path'] = info.gpt_path
    if (info.sovits_path is not None):
        os.environ['sovits_path'] = info.sovits_path
    if (info.cnhubert_base_path is not None):
        os.environ['cnhubert_base_path'] = info.cnhubert_base_path
    if (info.bert_path is not None):
        os.environ['bert_path'] = info.bert_path
        tts_pipeline.init_vits_weights(os.environ['sovits_path'])

class GenerateInfo(BaseModel):
    text: str = ""
    text_lang: str = "en"
    ref_audio_path: str
    aux_ref_audio_paths: list = []
    ref_audio_text: str
    ref_audio_lang: str = "en"
    top_k: int = 5
    top_p: float = 1.0
    temperature: float = 1.0
    text_split_method: str = "cut1" # Cut every four sentences
    batch_size: int = 20
    speed_factor: float = 1.0
    split_bucket: bool = True # TODO What is this?
    return_fragment: bool = False
    fragment_interval: float = 0.3 # TODO What is this?
    seed: Optional[int] = None
    parallel_infer: bool = True # TODO What is this?
    repetition_penalty: float = 1.35
    keep_random: bool = True

def generate_wrapper(info: GenerateInfo):
    seed = -1 if keep_random else seed
    actual_seed = seed if seed not in [-1, "", None] else random.randrange(1 << 32)
    for item in tts_pipeline.run(info.json()):
        chunk = {
            'item': item.tolist(),
            'actual_seed': actual_seed
        }
        yield json.dumps(chunk) # What is "item" anyways?
        # "item" seems to be (sr, audio) : (int, np.ndarray), but we don't know what the dimension is
        # np.concatenate(audio, 0) implies that the result is 1-dimensionaly
        # What are these chunks anyways?

# Going to diverge from their code here.
#@app.get("/find_models")

@app.post("/generate")
async def tts_generate(info: GenerateInfo):
    return StreamingResponse(generate_wrapper(info=info))

@app.post("/stop")
def tts_stop():
    tts_pipeline.stop()