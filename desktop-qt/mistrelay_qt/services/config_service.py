from __future__ import annotations

import json
from pathlib import Path

from ..models import AppConfig, DownloadConfig, ProxyConfig, UserInfo
from ..paths import ensure_runtime_dirs, legacy_tauri_config_path, qt_config_path


class ConfigService:
    def __init__(self) -> None:
        ensure_runtime_dirs()
        self._config_path = qt_config_path()
        self._config = self._load()

    @property
    def config(self) -> AppConfig:
        return self._config

    def _load(self) -> AppConfig:
        if self._config_path.exists():
            return AppConfig.from_dict(self._read_json(self._config_path))

        legacy = self._migrate_legacy_config()
        if legacy:
            self._write(legacy)
            return legacy

        fresh = AppConfig()
        self._write(fresh)
        return fresh

    def _migrate_legacy_config(self) -> AppConfig | None:
        legacy_path = legacy_tauri_config_path()
        if not legacy_path.exists():
            return None

        payload = self._read_json(legacy_path)
        proxy = payload.get("proxy") or {}
        download = payload.get("download") or {}
        return AppConfig(
            proxy=ProxyConfig(
                enabled=bool(proxy.get("enabled", False)),
                url=str(proxy.get("url") or ""),
            ),
            download=DownloadConfig(
                download_dir=str(download.get("downloadDir") or ""),
                max_concurrent_downloads=int(download.get("maxConcurrentDownloads") or 3),
                threads_per_download=int(download.get("threadsPerDownload") or 4),
            ),
        )

    def _read_json(self, path: Path) -> dict:
        try:
            return json.loads(path.read_text(encoding="utf-8"))
        except (FileNotFoundError, json.JSONDecodeError):
            return {}

    def _write(self, config: AppConfig) -> None:
        self._config_path.write_text(
            json.dumps(config.to_dict(), ensure_ascii=False, indent=2) + "\n",
            encoding="utf-8",
        )

    def save(self, config: AppConfig) -> AppConfig:
        self._config = config
        self._write(config)
        return self._config

    def save_user_session(
        self,
        *,
        server_base_url: str,
        token: str,
        user: dict | None,
    ) -> AppConfig:
        self._config.server_base_url = server_base_url.rstrip("/")
        self._config.auth_token = token
        self._config.user = UserInfo.from_dict(user)
        return self.save(self._config)

    def clear_user_session(self) -> AppConfig:
        self._config.auth_token = ""
        self._config.user = UserInfo()
        return self.save(self._config)

    def update_server_base_url(self, value: str) -> AppConfig:
        self._config.server_base_url = value.rstrip("/")
        return self.save(self._config)

    def update_runtime_settings(
        self,
        *,
        server_base_url: str,
        proxy_enabled: bool,
        proxy_url: str,
        download_dir: str,
        max_concurrent_downloads: int,
        threads_per_download: int,
    ) -> AppConfig:
        self._config.server_base_url = server_base_url.rstrip("/")
        self._config.proxy.enabled = proxy_enabled
        self._config.proxy.url = proxy_url.strip()
        self._config.download.download_dir = download_dir.strip()
        self._config.download.max_concurrent_downloads = max(1, int(max_concurrent_downloads))
        self._config.download.threads_per_download = max(1, int(threads_per_download))
        return self.save(self._config)
