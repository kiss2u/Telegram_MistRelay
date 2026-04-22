from __future__ import annotations

import os
from pathlib import Path


def config_root() -> Path:
    override = os.getenv("MISTRELAY_CONFIG_HOME")
    if override:
        return Path(override)

    appdata = os.getenv("APPDATA")
    if appdata:
        return Path(appdata) / "MistRelay"

    xdg = os.getenv("XDG_CONFIG_HOME")
    if xdg:
        return Path(xdg) / "MistRelay"

    return Path.home() / ".config" / "MistRelay"


def cache_root() -> Path:
    override = os.getenv("MISTRELAY_CACHE_HOME")
    if override:
        return Path(override)

    local_app_data = os.getenv("LOCALAPPDATA")
    if local_app_data:
        return Path(local_app_data) / "MistRelay"
    return config_root()


def preview_cache_root() -> Path:
    return cache_root() / "preview-cache"


def updates_root() -> Path:
    return cache_root() / "updates"


def logs_root() -> Path:
    return cache_root() / "logs"


def ensure_runtime_dirs() -> None:
    for path in (config_root(), cache_root(), preview_cache_root(), updates_root(), logs_root()):
        path.mkdir(parents=True, exist_ok=True)


def legacy_tauri_config_path() -> Path:
    return config_root() / "desktop-client.json"


def qt_config_path() -> Path:
    return config_root() / "desktop-client-qt.json"
