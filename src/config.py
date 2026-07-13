"""Load project configuration from config/config.yaml."""

from pathlib import Path
import yaml

_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_CONFIG_PATH = _PROJECT_ROOT / "config" / "config.yaml"


def load_config() -> dict:
    """Read and return the config dictionary.

    Raises FileNotFoundError with a helpful message if config.yaml
    hasn't been created from the template yet.
    """
    if not _CONFIG_PATH.exists():
        raise FileNotFoundError(
            f"Config file not found at {_CONFIG_PATH}.\n"
            "Copy config/config.template.yaml to config/config.yaml "
            "and fill in your connection details."
        )
    with open(_CONFIG_PATH, "r") as f:
        return yaml.safe_load(f)
