from __future__ import annotations

from urllib.parse import urlparse

from .runtime import release_metadata

ORGANIZATION_NAME = "MistRelay"
ORGANIZATION_DOMAIN = "mistrelay.local"

DEFAULT_WINDOW_WIDTH = 1440
DEFAULT_WINDOW_HEIGHT = 920
MIN_WINDOW_WIDTH = 1220
MIN_WINDOW_HEIGHT = 780

DEFAULT_DOWNLOAD_DIRNAME = "Downloads"
DEFAULT_MAX_CONCURRENT_DOWNLOADS = 3
DEFAULT_THREADS_PER_DOWNLOAD = 4
MIN_THREADS_PER_DOWNLOAD = 2
PREVIEW_READY_BYTES = 4 * 1024 * 1024
TRANSFER_PROGRESS_EMIT_INTERVAL = 0.5

_RELEASE_METADATA = release_metadata()
APP_NAME = _RELEASE_METADATA.product_name
UPDATE_MANIFEST_URL = _RELEASE_METADATA.manifest_url
UPDATE_SIGNATURE_URL = _RELEASE_METADATA.manifest_signature_url
UPDATE_RELEASE_FEED_URL = _RELEASE_METADATA.release_feed_url
UPDATE_RELEASE_TAG_PREFIX = _RELEASE_METADATA.release_tag_prefix
UPDATE_VERIFY_KEY = _RELEASE_METADATA.verify_key


def _asset_name_from_url(url: str, default: str) -> str:
    candidate = urlparse(url).path.rsplit("/", 1)[-1].strip()
    return candidate or default


UPDATE_MANIFEST_ASSET_NAME = _asset_name_from_url(UPDATE_MANIFEST_URL, "qt-latest.json")
UPDATE_SIGNATURE_ASSET_NAME = _asset_name_from_url(
    UPDATE_SIGNATURE_URL,
    f"{UPDATE_MANIFEST_ASSET_NAME}.sig",
)

ROUTES = ("dashboard", "downloads", "drive", "settings")

ROUTE_TITLES = {
    "dashboard": "概览面板",
    "downloads": "任务中心",
    "drive": "网盘浏览",
    "settings": "系统设置",
}
