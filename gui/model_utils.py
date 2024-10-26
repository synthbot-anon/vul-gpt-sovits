from pathlib import Path
from logging import warn
from huggingface_hub import list_repo_files
import os

def find_models_hf(
    repo_name: str
):
    """ Searches a huggingface repo, organized by character/model name folder, for compatible models.
    Outputs a dict:
    {'Mane6-SVe12-GPTe8': {
        'gpt_weight': 'Mane6-SVe12-GPTe8/GPT_weights_v2/Mane6-e8.ckpt',
        'sovits_weight': 'Mane6-SVe12-GPTe8/SoVITS_weights_v2/Mane6_e12_s28248.pth',
    }}
    """
    repo_files = list_repo_files(repo_name)
    model_map = {}
    SoVITS_weight_root=["SoVITS_weights_v2","SoVITS_weights"]
    GPT_weight_root=["GPT_weights_v2","GPT_weights"]

    for file in repo_files:
        # .pth -> sovits file
        if file.endswith(".pth"):
            model_name = os.path.dirname(file)
            # Seek parent that is not a weight root name
            while model_name != '':
                if os.path.basename(model_name) not in SoVITS_weight_root:
                    break
                model_name = os.path.dirname(model_name)
                
            if model_name == '':
                if not repo_name in model_map:
                    model_map[repo_name] = {}
                model_map[repo_name]['sovits_weight'] = file
            else:
                if not model_name in model_map:
                    model_map[model_name] = {}
                model_map[model_name]['sovits_weight'] = file

        # .ckpt -> gpt file
        if file.endswith(".ckpt"):
            model_name = os.path.dirname(file)
            # Seek parent that is not a weight root name
            while model_name != '':
                if os.path.basename(model_name) not in GPT_weight_root:
                    break
                model_name = os.path.dirname(model_name)
                
            if model_name == '':
                if not repo_name in model_map:
                    model_map[repo_name] = {}
                model_map[repo_name]['gpt_weight'] = file
            else:
                if not model_name in model_map:
                    model_map[model_name] = {}
                model_map[model_name]['gpt_weight'] = file
                
    # filter out incomplete models (need both weights)
    model_map = {k:v for k,v in model_map.items() if (
        'gpt_weight' in v and 'sovits_weight' in v)}
                
    return model_map

def find_models(
    base_dir: Path,
    models_folder_dir: Path
):
    """
    Finds models local to this filesystem. (i.e. only makes sense to run
    serverside).
    `base_dir`: GPT-SoVITS base directory - the install directory by default
    `models_folder_dir`: models directory, for character models - by default, a "models" directory inside install
    A character model directory should contain exactly one GPT weight and one SoVITS weight.
    """
    ret = {
        'loose_models': {
            'sovits_weights': [],
            'gpt_weights': []
        },
        'folder_models': []
    }
    if isinstance(base_dir, str):
        base_dir = Path(base_dir)
    if isinstance(models_folder_dir, str):
        models_folder_dir = Path(models_folder_dir)

    # collect base dir models first
    SoVITS_weight_root=["SoVITS_weights_v2","SoVITS_weights"]
    GPT_weight_root=["GPT_weights_v2","GPT_weights"]
    for root in SoVITS_weight_root:
        if not (base_dir / root).exists():
            continue
        models = (base_dir / root).glob("*.pth")
        models = [str(g.absolute()) for g in models]
        ret['loose_models']['sovits_weights'] : list
        ret['loose_models']['sovits_weights'].extend(models)
    for root in GPT_weight_root:
        if not (base_dir / root).exists():
            continue
        models = (base_dir / root).glob("*.ckpt")
        models = [str(g.absolute()) for g in models]
        ret['loose_models']['gpt_weights'] : list
        ret['loose_models']['gpt_weights'].extend(models)
        
    if not models_folder_dir.exists():
        return ret

    # Then collect character models
    for d in models_folder_dir.iterdir():
        d: Path
        model_name = d.name
        model_ret = {}
        SoVITS_weights = d.rglob('*.pth')
        SoVITS_weights = [str(g.absolute()) for g in SoVITS_weights]
        if len(SoVITS_weights) < 1:
            warn(f"Could not find a SoVITS weight for model folder {str(d)}")
            continue
        GPT_weights = d.rglob('*.ckpt')
        GPT_weights = [str(g.absolute()) for g in GPT_weights]
        if len(GPT_weights) < 1:
            warn(f"Could not find a GPT weight for model folder {str(d)}")
            continue
        model_ret['model_name'] = model_name
        model_ret['sovits_weight'] = SoVITS_weights[0]
        model_ret['gpt_weight'] = GPT_weights[0]
        ret['loose_models']['sovits_weights'].append(model_ret['sovits_weight'])
        ret['loose_models']['gpt_weights'].append(model_ret['gpt_weight'])
        ret['folder_models'].append(model_ret)
    
    return ret