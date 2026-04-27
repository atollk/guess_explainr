import contextlib
import json
import logging
import os.path
from collections.abc import Iterator
from dataclasses import dataclass

import platformdirs

from guess_explainr import model_provider

_dirs = platformdirs.PlatformDirs("guess_explainr")
_config_file = os.path.join(_dirs.user_config_dir, "config.json")
logging.info(f"Loading config from {_config_file}")
os.makedirs(os.path.dirname(_config_file), exist_ok=True)


@dataclass
class PanoramaState:
    panorama_id: str | None = None
    panorama_image_bytes: bytes | None = None


@dataclass
class PlonkitSyncState:
    ready: bool = False
    total: int = 0
    done: int = 0
    error: str | None = None


panorama_state = PanoramaState()
plonkit_sync_state = PlonkitSyncState()


@dataclass
class StateConfig:
    ai_provider: model_provider.ModelProvider | None = None
    ai_model: str | None = None
    api_key: str | None = None
    maps_api_key: str | None = None


def get_config() -> StateConfig:
    try:
        with open(_config_file) as f:
            config = json.load(f)
    except (FileNotFoundError, json.JSONDecodeError):
        return StateConfig()
    try:
        return StateConfig(
            ai_provider=model_provider.ModelProvider(config["ai_provider"]),
            ai_model=config["ai_model"],
            api_key=config["api_key"],
            maps_api_key=config.get("maps_api_key") or None,
        )
    except (TypeError, AttributeError, KeyError, ValueError):
        return StateConfig()


def set_config(config: StateConfig) -> None:
    with open(_config_file, "w") as f:
        d = {
            "ai_provider": config.ai_provider.value if config.ai_provider else None,
            "ai_model": config.ai_model,
            "api_key": config.api_key,
            "maps_api_key": config.maps_api_key or None,
        }
        json.dump(d, f)


@contextlib.contextmanager
def modify_config() -> Iterator[StateConfig]:
    config = get_config()
    yield config
    set_config(config)
