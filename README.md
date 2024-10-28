# What is this?
Implements a server/client GUI for GPT-SoVITS.

Features:
- Safetensors only
- Reference audio management
  * Pony Preservation Project format filename parsing
- Semi-remote model management
- Parallelized repeated generations 
- Rich audio preview with drag and drop
- Bugfixes to the original repo (invalidating cache for change in prompt lang)

# Instructions - client 
## Installation
### Use from pyinstaller (Windows)
The client uses approx. 220 MB of disk space.
### Use from source (other) (minimum python=3.10)
Clone the repository. In a venv or conda environment install `requirements_client.txt`. Then launch the gui with `python gui_client.py`.

# Instructions - server
The server is (at least currently) not intended for concurrent use by multiple users; it doesn't have proper handling for concurrent requests. 

## Installation
### Use from pyinstaller (Windows)
The server uses approx. 10 GB of disk space including the models that ship with the server by default (Mane 6).
### Use from source (other) (recommend python=3.10)
1. Clone the repository. Set up a conda environment if you wish.
2. Install `ffmpeg` (**see the original repo's instructions further below for installing on different OSes!**).
3. Install pytorch 2.3.0: `pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu118`
5. In a venv or conda environment install `requirements.txt` and `requirements_server.txt`
6. Then launch the server with `python gui_server.py`. The server will automatically download the necessary pretrained models for inference on startup.

### Ngrok
Hahaha just kidding you need a "verified account" now.

# FAQ
* **Why a client/server model?** Because I didn't realize that ngrok requires accounts now and I was under the impression that you would be able to host a model from Colab.
* **Why can't I select some files as primary references?** GPT-SoVITS disallows using audios shorter than 3 seconds or longer than 10 seconds as a primary reference audio (not sure why). You can, however, work around this by stitching together/cutting audio files in an audio editor.
* **Why is Twilight Sparkle underneath the drag and drop cursor?** Because PyQt5 starts screaming into the console if the drag pixmap is nothing.