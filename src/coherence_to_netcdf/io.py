import yaml
from typing import Dict, Any


def load_yaml(path: str) -> Dict[str, Any]:
    """Load a YAML file into a Python dictionary."""
    with open(path, "r") as f:
        return yaml.safe_load(f) or {}