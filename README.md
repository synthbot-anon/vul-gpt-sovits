# What is this?
Implements a GUI for GPT-SoVITS.

![Overall GUI](/../standalone_gui/docs/screenshots/overall.png)

Features:
- Reference audio management
  * Pony Preservation Project format filename parsing
  * Builtin downloader for Clipper's Master File
- Add models from a huggingface repo in the GUI
- Parallelized repeated generations 
- Rich audio preview with drag and drop
- Experimental custom ARPAbet support (english only)
  * Type in ARPAbet in curly braces, e.g. `{D IH0 S P EH1 N S ER0}`
  * Vowel stress numbers are required.
- Bugfixes to the original repo (invalidating cache for change in prompt lang)

# Instructions 
An NVIDIA GPU is recommended. You can get away with 4 GB VRAM but higher is better. CPU-only inference is possible, but slow (~9x slower).

## Installation
### ffmpeg
GPT-SoVITS depends on FFmpeg, which is bundled with the Windows pyinstaller. If using from source, follow the below instructions:

#### Conda Users
```bash
conda install ffmpeg
```

#### Ubuntu/Debian Users
```bash
sudo apt install ffmpeg
sudo apt install libsox-dev
```

#### Windows Users
Download and place [ffmpeg.exe](https://huggingface.co/lj1995/VoiceConversionWebUI/blob/main/ffmpeg.exe) and [ffprobe.exe](https://huggingface.co/lj1995/VoiceConversionWebUI/blob/main/ffprobe.exe) in the GPT-SoVITS root.

Install [Visual Studio 2017](https://aka.ms/vs/17/release/vc_redist.x86.exe) (Korean TTS Only)

#### MacOS Users
```bash
brew install ffmpeg
```

### From pyinstaller (Windows)
The pyinstaller build uses approx. 10 GB of disk space including pretrained models bundled with it. As this is too large for GitHub, the latest release is hosted [here](https://drive.google.com/file/d/1dgG1kg0e9p4khrwpPaI9NdV_PIiMDGOZ/view) and can be run simply by executing `gptsovits.exe`. The client will automatically download the necessary pretrained models for inference on startup.

Also see: [Build folder](https://drive.google.com/drive/folders/141YfYH_GS29D80kAcKljmXgN91zKLbUq)
[CPU-only pytorch version](https://drive.google.com/file/d/1FVuwuKyUqfuRcHVKr-ACgAul4araUjPN/view?usp=drive_link)

### From source (other) (recommend python=3.10)
1. Clone the repository. 
  * Set up a conda environment if you wish: `conda create -n GPTSovitsClient python=3.10`
    - Activate the environment: `conda activate GPTSovitsClient`
  * Or set up a venv if you wish: `python -m venv GPTSovitsClient`
    - Activate the environment (Unix/MacOS): `source GPTSovitsClient/bin/activate`
    - Activate the environment (Windows): `GPTSovitsClient\Scripts\activate`
2. Install pytorch 2.3.0: `pip install torch==2.3.0 torchvision==0.18.0 torchaudio==2.3.0 --index-url https://download.pytorch.org/whl/cu118`
3. `pip install -r requirements.txt -r requirements_client.txt`
4. Then launch the server with `python gui_client.py`. The client will automatically download the necessary pretrained models for inference on startup.

### Troubleshooting
- On Windows -- if audio playback fails mentioning `DirectShowPlayerService error`, this is a codec issue. Try installing [K-Lite Codecs](https://codecguide.com/download_kl.htm).
- On Linux: The GUI uses the PyQt5 multimedia library and gstreamer which may not be installed on your distro.
  - On Ubuntu or other apt distros, try `apt install libqt5multimedia5 libgstreamer1.0-dev libgstreamer-plugins-bad1.0-dev libgstreamer-plugins-base1.0-dev libgstreamer-plugins-good1.0-dev`
  - If not using apt, try to find and install the equivalent packages for your distro.
- `RuntimeError: Failed to load Audio`. This is because ffmpeg could not be detected on your system. Ensure that ffmpeg is installed according to the provided instructions above.

## DPI scaling
- If you are using a high DPI monitor, run the program first. A config file called `effusive_gui_config.yaml` will appear.
- Set `enable_hi_dpi` to `True`.

## Usage
- **Starting the program.** Be patient -- there's a lot of Python in there! It takes me minimum 10 seconds to start seeing console output.
### Adding models. 
By default, the pyinstaller version comes "batteries included" with Mane 6 voices for TTS, but it will only have the base GPT-SoVITS model if you opted for a source install. You may be interested in downloading other models from a huggingface repo. This can be done from within the interface by clicking on the **Add Model** action in the toolbar. Typically, each model occupies ~220 MB of disk space.

1. Specify the huggingface repo id in `HF Repo:` and hit enter.
2. Select the desired model to download.
3. Click `add to server` and wait for the model to download.

![Adding models](/../standalone_gui/docs/screenshots/addmodel.png)

- Currently, this tool expects the huggingface repo to be laid out in a certain way; see [this repo](https://huggingface.co/therealvul/GPT-SoVITS-v2) for an example. I did not use `.zip` because it can obscure the directory structure.
- Models downloaded this way are placed in the `models` directory which is created if it does not exist.
- (pyinstaller) You can also manually add "loose" models (i.e. models not coupled to any particular character) by creating `GPT_weights_v2` and `SoVITS_weights_v2` directories next to the .exe and placing the weights in those respective directories.

### Model selection
*Note that the initial model when the GUI is first loaded is the base model, which is not finetuned on any particular characters. Download and load a more specific model for better results.*

Under this section, you can select either individual weights or speaker-bundled weights (i.e. paired GPT and SoVITS weights corresponding to a particular speaker, typically downloaded using the above `Add Model` action and located in the `models` directory.). 

![Selecting models](/../standalone_gui/docs/screenshots/selectmodel.png)

- To load the selected model, you must click `Load selected models`. 
- You can refresh the lists of available models from your filesystem by clicking `Refresh available models`.

### Reference audios
GPT-SoVITS accepts reference audio clips which can be used to control the intonation and timbre of the resulting generated speech. The Reference Audios section allows for the inputting, labeling, organization, and selection of reference audio for your generations. If you wish to download reference audio clips from Clipper's Master File, click the `Master file downloader` option at the top of the screen (see section `Master File Downloader` for more info)

![Reference audios](/../standalone_gui/docs/screenshots/refaudios.png)

- **One "required" field you must fill out for generation is `Utterance`,** which you should fill with a transcription of what is spoken in the reference audio.
- **One primary reference audio must be selected for generation.** The primary reference audio tends to control more overall pitch and intonation over timbre, while the aux reference audios have more control over timbre.
- All other editable fields and filters are purely for organization purposes.
- Audio following the PPP dataset naming format, e.g. `00_03_24_Pinkie_Happy_Noisy_There's a chance i may have missed a note or two Here or there, but i just love playing so much!.flac`, will automatically have their data fields filled out by parsing the file name.
- (pyinstaller) The pyinstaller build, in addition to the Mane 6 models, also comes with corresponding [reference audios](https://drive.google.com/file/d/1EljbxeUckYATH269utj7q1T-8oKcPhte/view?usp=drive_link) that can produce reasonable quality generations.

### Inference
The words to be spoken can be filled out under **Text prompt**. When ready to submit, click the **Generate** button to begin generation. Generations will appear under the **Generations** section, which can be previewed. In addition, you can drag and drop the resulting generated audio files from the play button icon into other programs.

- The audio is outputted in an `outputs` directory by default.
- The audio waveform preview supports drag+click to seek and spacebar to toggle playback.

![Inference](/../standalone_gui/docs/screenshots/inference.png)

- **Repetitions** can be used to generate, in parallel, multiple versions of the same prompt text, each of which will be displayed in the Generations section.
  * This is particularly useful for content creation purposes where you may be editing together multiple audio clips and looking for generations with specific inflections or other characteristics.
  * Setting a fixed seed for multiple repetitions is pointless (they will all be the same).
- A notable parameter for controlling memory usage is **batch size**. Higher batch sizes will result in higher maximum memory usage.
  * GPT-SoVITS only uses as many batches as it needs--so with a small number of batches and a low number of repetitions, your memory usage may not reflect the maximum amount of memory usage possible for a particular batch size.

### Master file downloader
The Master file downloader offers a basic interface to search and download reference audio files from Clipper's Master File. To do this it must first build an index of the available files; depending on network speed this can take anywhere from 20 seconds to multiple minutes.

![Master file downloader](/../standalone_gui/docs/screenshots/masterfile.png)

The `Glob search` field accepts glob-style filename patterns, i.e. `*_Rarity_*`. `Sort`
allows you to sort by file length. `Rebuild master file index` can be used to rebuild the index, which can be useful if the Master File is updated in the future.

# Building
A conda environment appropriately set up to run the client, plus pyinstaller, on Windows, should allow you to run `pyinstaller gptsovits_client.spec` which should reproduce the pyinstaller (minus bundled reference audios and models).

# FAQ
* **Why is Twilight Sparkle underneath the drag and drop cursor?** Because PyQt5 starts screaming into the console if the drag pixmap is nothing.
* **Why am I running out of memory?** Very long sentences and using too high of a batch size can both increase your VRAM usage; consider lowering them according to your available GPU resources.
  - **Text split** applies directly to this. For example, "batch every 4 sentences" will result in longer items per batch increasing overall VRAM usage.
  - Higher `n_repetitions` can "fill out" batches more quickly, but the limiting factor should still be batch size.
* **Why is interrupt spotty?** Internally the way GPT-SoVITS has implemented this is just by setting a flag that's checked in the middle of generation. I'm not sure if there's a more robust way to interrupt the generation process.
* **Why is the text prompt area so small?** It is to discourage you from using excessively long prompts which could trigger OOM issues, since I don't have a robust way of dealing with OOM right now. But you are allowed to type/paste in as much text as you think you want.

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