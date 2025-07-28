from __future__ import annotations

import json
from pathlib import Path


SETTINGS_PATH = Path(__file__).with_name("settings.json")

try:
    with SETTINGS_PATH.open("r") as f:
        _SETTINGS = json.load(f)
except FileNotFoundError:
    _SETTINGS = {}


def get_setting(key: str, default: str | None = None) -> str | None:
    """Return the configured value for ``key`` or ``default`` if missing."""
    return _SETTINGS.get(key, default)
