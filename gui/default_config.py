from omegaconf import OmegaConf

default_config = {
    "ref_audios_dir": "ref_audios",
    "outputs_dir": "outputs",
    "num_gens": 3,
    "inference": {
        "top_k": 5,
        "top_p": 1.0,
        "temperature": 1.0,
        "text_split_method": 'cut4',
        "batch_size": 10, # A larger is typically not needed
        "speed_factor": 1.0,
        "fragment_interval": 0.3,
        "repetition_penalty": 1.35
    }
}