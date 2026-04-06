"""CLI configuration management - ~/.aegis/config.toml."""

from __future__ import annotations

import os
from pathlib import Path
from typing import Any

import toml


CONFIG_DIR = Path.home() / ".aegis"
CONFIG_FILE = CONFIG_DIR / "config.toml"


def get_config_dir() -> Path:
    CONFIG_DIR.mkdir(parents=True, exist_ok=True)
    return CONFIG_DIR


def load_cli_config() -> dict[str, Any]:
    if not CONFIG_FILE.exists():
        return {}
    try:
        return toml.load(CONFIG_FILE)
    except Exception:
        return {}


def save_cli_config(config: dict[str, Any]) -> None:
    get_config_dir()
    with open(CONFIG_FILE, "w") as f:
        toml.dump(config, f)


def get_api_url() -> str:
    config = load_cli_config()
    return config.get("api_url", os.environ.get("AEGIS_API_URL", "http://localhost:8000"))


def get_api_key() -> str | None:
    config = load_cli_config()
    return config.get("api_key", os.environ.get("AEGIS_API_KEY"))
