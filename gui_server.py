from fastapi import FastAPI, Response
from starlette.responses import StreamingResponse
from pydantic import BaseModel
from typing import Optional
import os, re, logging
import sys
import torch
import json
import random
import base64
import numpy as np
from pathlib import Path
import uvicorn
from peewee import *
from gui.database import GPTSovitsDatabase, RefAudio, SERVER_DB_FILE
from gui.util import (get_available_filename, sanitize_filename,
    base64_to_audio_file)

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
database = GPTSovitsDatabase(db_file=SERVER_DB_FILE)
LOCAL_REF_SOUNDS_FOLDER = 'ref_sounds/'
os.makedirs(LOCAL_REF_SOUNDS_FOLDER, exist_ok=True)
    
from gui import model_utils
@app.post("/find_models")
def find_models():
    return model_utils.find_models(
        Path(now_dir),
        Path(now_dir) / "models",)


class UploadRefAudioInfo(BaseModel):
    audio_hash: str
    base64_audio_data: Optional[str] = None
    preferred_name: Optional[str] = None
    utterance: Optional[str] = None

    local_filepath: Optional[str] = None
    # The client should only transmit local_filepath if it detects that it and
    # the server are on the same machine (i.e. communicating via localhost or 
    # 127.0.0.1)

# method for uploading and updating reference audio
@app.post("/post_ref_audio")
def post_ref_audio(info : UploadRefAudioInfo, response: Response):

    preferred_name = info.audio_hash+'.ogg'
    if info.preferred_name is not None:
        preferred_name = info.preferred_name
        preferred_name = os.path.splitext(info.preferred_name)[0]
        if not preferred_name.endswith('.ogg'):
            preferred_name = preferred_name + '.ogg'

    if info.base64_audio_data is None and not info.local_filepath:
        # If base64_audio_data is null and this is not a local file, 
        # then we are updating, and the ref audio must already exist on disk.
        ref_audio : Optional[RefAudio] = database.get_ref_audio(info.audio_hash)
        if ref_audio is None or not Path(ref_audio.local_filepath):
            raise HTTPException(status_code=404,
                detail=f"Attempted to update ref audio not found on disk: "
                    f"{ref_audio.local_filepath} ({ref_audio.audio_hash})")
        
        ref_audio.utterance = info.utterance
        ref_audio.save()
        response.status_code = 200
        return

    if not info.local_filepath:
        # Then we need to interpret base64_audio_data and save to disk
        preferred_name = sanitize_filename(preferred_name)
        local_filepath = Path(LOCAL_REF_SOUNDS_FOLDER) / preferred_name
        local_filepath = get_available_filename(str(local_filepath))
        
        base64_to_audio_file(
            info.base64_audio_data,
            local_filepath)
    else:
        if not Path(info.local_filepath).exists():
            raise HTTPException(status_code=404,
                detail=f"Specified local filepath {ref_audio.local_filepath} "
                    f"not found by server")

    database.update_with_ref_audio(
        audio_hash=info.audio_hash,
        local_filepath=local_filepath,
        utterance=info.utterance)
    response.status_code = 201
    return


@app.post("/download_hf_models")
def download_hf_models():
    pass


@app.get("/db_path")
def db_path():
    return Path(SERVER_DB_FILE).absolute()
    

@app.get("/list_ref_audio")
def list_ref_audio():
    v: RefAudio
    return {v.audio_hash: {
        'filepath': v.local_filepath,
        'utterance': v.utterance
    } for v in database.list_ref_audio()}
    

class TestHashesInfo(BaseModel):
    hashes: list[str] = []

@app.get("/test_hashes")
def test_hashes(info: TestHashesInfo):
    return database.test_hashes(info.hashes)


class SetModelsInfo(BaseModel):
    gpt_path: Optional[str] = None
    sovits_path: Optional[str] = None
    cnhubert_base_path: Optional[str] = None
    bert_path: Optional[str] = None

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
    tts_pipeline.init_t2s_weights(os.environ['gpt_path'])
    tts_pipeline.init_vits_weights(os.environ['sovits_path'])
    return {
        'gpt_path': tts_pipeline.configs.vits_weights_path,
        'sovits_path': tts_pipeline.configs.t2s_weights_path
    }

class GenerateInfo(BaseModel):
    text: str = ""
    text_lang: str = "en"
    ref_audio_hash: Optional[str] = None
    aux_ref_audio_hashes: Optional[list] = None
    prompt_text: Optional[str] = None
    prompt_lang: str = "en"
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

async def generate_wrapper(info: GenerateInfo):
    seed = -1 if info.keep_random else seed
    actual_seed = seed if seed not in [-1, "", None] else random.randrange(1 << 32)
    for item in tts_pipeline.run(json.loads(info.json())):
        sr, audio = item
        chunk = {
            'sr': sr,
            'audio': base64.b64encode(audio).decode("ascii"),
            'actual_seed': actual_seed
        }
        yield json.dumps(chunk) # What is "item" anyways?
        # "item" seems to be (sr, audio) : (int, np.ndarray), but we don't know what the dimension is
        # np.concatenate(audio, 0) implies that the result is 1-dimensionaly
        # What are these chunks anyways?

@app.post("/generate")
async def tts_generate(info: GenerateInfo):
    return StreamingResponse(generate_wrapper(info=info))


@app.head("/test")
def test_conn():
    pass


@app.post("/stop")
def tts_stop():
    tts_pipeline.stop()
    
if __name__ == '__main__':
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument('--ngrok',
        action='store_true')
    
    args = parser.parse_args()

    port = 17157
    if args.ngrok:
        from pyngrok import ngrok
        public_url = ngrok.connect(port)
        print(f"ngrok tunnel opened at {public_url}")
    uvicorn.run(app, host="0.0.0.0", port=port)