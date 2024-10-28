from omegaconf import OmegaConf

DEFAULT_CONFIG_PATH = "effusive_gui_config.yaml"
default_config = {
    "enable_hi_dpi": False,
    "ref_audios_dir": "ref_audios",
    "outputs_dir": "outputs",
    "models_dir": "models",
    "inference": {
        "top_k": 5,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": 'cut4',
        "batch_size": 10, # A larger is typically not needed
        "speed_factor": 1.0,
        "fragment_interval": 0.3,
        "repetition_penalty": 1.35,
        'use_random': True,
        "n_repetitions": 3,
        # OOMs are hard to recover from, so we set the batch size
        # to a relatively low value
        'max_batch_size': 20
    },
}