import yaml
import os

def load_config(config_path='configs/annotator.yaml'):
    """Load configuration from YAML file"""
    with open(config_path, 'r') as f:
        config = yaml.safe_load(f)
    return config
