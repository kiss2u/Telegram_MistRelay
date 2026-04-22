from __future__ import annotations

import json
import os
import sys
from dataclasses import dataclass
from functools import lru_cache
from pathlib import Path


@dataclass(frozen=True, slots=True)
class ReleaseMetadata:
    version: str
    channel: str
    product_name: str
    release_tag_prefix: str
    manifest_url: str
    release_feed_url: str
    verify_key: str

    @property
    def manifest_signature_url(self) -> str:
        if not self.manifest_url:
            return ""
        return f"{self.manifest_url}.sig"


def is_packaged() -> bool:
    return bool(getattr(sys, "frozen", False))


def repo_root() -> Path:
    return Path(__file__).resolve().parents[2]


def resource_root() -> Path:
    meipass = getattr(sys, "_MEIPASS", None)
    if meipass:
        return Path(meipass)
    return repo_root() / "desktop-qt"


def app_executable() -> Path:
    return Path(sys.executable if is_packaged() else (resource_root() / "main.py"))


def resolve_resource(*parts: str) -> Path:
    candidate = resource_root().joinpath(*parts)
    if candidate.exists() or is_packaged():
        return candidate
    return repo_root().joinpath(*parts)


def version_file_path() -> Path:
    return resolve_resource("version.json")


@lru_cache(maxsize=1)
def release_metadata() -> ReleaseMetadata:
    payload = _read_release_payload()
    version = str(payload.get("version") or "0.0.0-dev")
    channel = str(payload.get("channel") or "dev")
    product_name = str(payload.get("product_name") or "MistRelay Desktop Qt")
    release_tag_prefix = str(payload.get("release_tag_prefix") or "desktop-qt-v")
    manifest_override = os.getenv("MISTRELAY_QT_UPDATE_MANIFEST_URL")
    manifest_url = str(
        manifest_override
        or payload.get("manifest_url")
        or ""
    ).strip()
    release_feed_url = str(
        ""
        if manifest_override
        else os.getenv("MISTRELAY_QT_UPDATE_RELEASE_FEED_URL")
        or payload.get("release_feed_url")
        or ""
    ).strip()
    verify_key = str(
        os.getenv("MISTRELAY_QT_UPDATE_VERIFY_KEY")
        or os.getenv("QT_UPDATE_VERIFY_KEY")
        or payload.get("verify_key")
        or ""
    ).strip()
    return ReleaseMetadata(
        version=version,
        channel=channel,
        product_name=product_name,
        release_tag_prefix=release_tag_prefix,
        manifest_url=manifest_url,
        release_feed_url=release_feed_url,
        verify_key=verify_key,
    )


def _read_release_payload() -> dict[str, object]:
    path = version_file_path()
    if not path.exists():
        return {}

    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except (OSError, json.JSONDecodeError):
        return {}
