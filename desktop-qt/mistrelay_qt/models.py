from __future__ import annotations

from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any

from .constants import (
    DEFAULT_MAX_CONCURRENT_DOWNLOADS,
    DEFAULT_THREADS_PER_DOWNLOAD,
)


@dataclass(slots=True)
class ProxyConfig:
    enabled: bool = False
    url: str = ""


@dataclass(slots=True)
class DownloadConfig:
    download_dir: str = ""
    max_concurrent_downloads: int = DEFAULT_MAX_CONCURRENT_DOWNLOADS
    threads_per_download: int = DEFAULT_THREADS_PER_DOWNLOAD


@dataclass(slots=True)
class UserInfo:
    id: int | None = None
    username: str = ""
    role: str = ""

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "UserInfo":
        if not payload:
            return cls()
        return cls(
            id=payload.get("id"),
            username=str(payload.get("username") or ""),
            role=str(payload.get("role") or ""),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass(slots=True)
class AppConfig:
    server_base_url: str = ""
    auth_token: str = ""
    user: UserInfo = field(default_factory=UserInfo)
    proxy: ProxyConfig = field(default_factory=ProxyConfig)
    download: DownloadConfig = field(default_factory=DownloadConfig)

    @classmethod
    def from_dict(cls, payload: dict[str, Any] | None) -> "AppConfig":
        payload = payload or {}
        proxy = payload.get("proxy") or {}
        download = payload.get("download") or {}

        legacy_download_dir = download.get("downloadDir", "")
        legacy_max_concurrent = download.get("maxConcurrentDownloads")
        legacy_threads = download.get("threadsPerDownload")

        return cls(
            server_base_url=str(
                payload.get("server_base_url")
                or payload.get("serverBaseUrl")
                or ""
            ),
            auth_token=str(
                payload.get("auth_token")
                or payload.get("authToken")
                or ""
            ),
            user=UserInfo.from_dict(payload.get("user")),
            proxy=ProxyConfig(
                enabled=bool(proxy.get("enabled", False)),
                url=str(proxy.get("url") or ""),
            ),
            download=DownloadConfig(
                download_dir=str(download.get("download_dir") or legacy_download_dir or ""),
                max_concurrent_downloads=int(
                    download.get("max_concurrent_downloads")
                    or legacy_max_concurrent
                    or DEFAULT_MAX_CONCURRENT_DOWNLOADS
                ),
                threads_per_download=int(
                    download.get("threads_per_download")
                    or legacy_threads
                    or DEFAULT_THREADS_PER_DOWNLOAD
                ),
            ),
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "server_base_url": self.server_base_url,
            "auth_token": self.auth_token,
            "user": self.user.to_dict(),
            "proxy": asdict(self.proxy),
            "download": asdict(self.download),
        }


@dataclass(slots=True)
class UpdateInfo:
    available: bool
    version: str = ""
    notes: str = ""
    pub_date: str = ""
    installable: bool = False
    manual_url: str = ""
    message: str = ""
    signature_verified: bool = False
    download_url: str = ""
    sha256: str = ""
    size: int = 0


@dataclass(slots=True)
class DownloadedUpdate:
    version: str
    installer_path: Path
    download_url: str
    sha256: str
    size: int


@dataclass(slots=True)
class TransferStatus:
    transfer_id: str
    file_name: str
    local_path: Path
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    download_speed: float = 0.0
    progress_percent: float = 0.0
    state: str = "pending"
    ready_for_preview: bool = False
    error: str = ""
