# What is this?
Implements a GUI for GPT-SoVITS.

Features:
- Reference audio management
  * Pony Preservation Project format filename parsing
- Add models from a huggingface repo in the GUI!
- Parallelized repeated generations 
- Rich audio preview with drag and drop
- Bugfixes to the original repo (invalidating cache for change in prompt lang)

# Instructions 
## Installation
### Use from pyinstaller (Windows)
The GUI program uses approx. 10 GB of disk space including pretrained models bundled with it. As this is too large for GitHub, the latest release is hosted here.
### Use from source (other) (recommend python=3.10)
1. Clone the repository. Set up a conda environment if you wish
2. Install `ffmpeg` (see the original repo's instructions further below for installing on different OSes!)
3. Install pytorch 2.3.0: `pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu118`
4. In a venv or conda environment install `requirements.txt` and `requirements_client.txt`
5. Then launch the server with `python gui_client.py`. The client will automatically download the necessary pretrained models for inference on startup.

# FAQ
* **Why can't I select some files as primary references?** GPT-SoVITS disallows using audios shorter than 3 seconds or longer than 10 seconds as a primary reference audio (not sure why). You can, however, work around this by stitching together/cutting audio files in an audio editor.
* **Why is Twilight Sparkle underneath the drag and drop cursor?** Because PyQt5 starts screaming into the console if the drag pixmap is nothing.
* **Why am I running out of memory?** Very long sentences and using too high of a batch size can both increase your VRAM usage; consider lowering them according to your available GPU resources.
  - Higher `n_repetitions` can "fill out" batches more quickly, but the limiting factor should still be batch size.
* **Why is interrupt spotty?** Internally the way GPT-SoVITS has implemented this is just by setting a flag that's checked in the middle of generation. I'm not sure if there's a more robust way to interrupt the generation process.

#### Install FFmpeg

##### Conda Users

```bash
conda install ffmpeg
```

##### Ubuntu/Debian Users

```bash
sudo apt install ffmpeg
sudo apt install libsox-dev
conda install -c conda-forge 'ffmpeg<7'
```

##### Windows Users

Download and place [ffmpeg.exe](https://huggingface.co/lj1995/VoiceConversionWebUI/blob/main/ffmpeg.exe) and [ffprobe.exe](https://huggingface.co/lj1995/VoiceConversionWebUI/blob/main/ffprobe.exe) in the GPT-SoVITS root.

Install [Visual Studio 2017](https://aka.ms/vs/17/release/vc_redist.x86.exe) (Korean TTS Only)

##### MacOS Users
```bash
brew install ffmpeg
```