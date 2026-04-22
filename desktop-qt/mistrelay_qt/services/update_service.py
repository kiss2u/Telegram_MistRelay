from __future__ import annotations

import base64
import hashlib
import json
import os
import subprocess
import sys
import tempfile
from contextlib import contextmanager
from pathlib import Path
from typing import TYPE_CHECKING
from urllib.parse import urlparse

from ..constants import (
    APP_NAME,
    UPDATE_MANIFEST_ASSET_NAME,
    UPDATE_MANIFEST_URL,
    UPDATE_RELEASE_FEED_URL,
    UPDATE_RELEASE_TAG_PREFIX,
    UPDATE_SIGNATURE_ASSET_NAME,
    UPDATE_SIGNATURE_URL,
    UPDATE_VERIFY_KEY,
)
from ..models import DownloadedUpdate, UpdateInfo
from ..paths import updates_root

if TYPE_CHECKING:
    import httpx


def normalize_version(value: str) -> list[str]:
    return [part for part in value.strip().removeprefix("v").split(".") if part]


def compare_versions(left: str, right: str) -> int:
    left_parts = normalize_version(left)
    right_parts = normalize_version(right)
    max_length = max(len(left_parts), len(right_parts))
    for index in range(max_length):
        raw_left = left_parts[index] if index < len(left_parts) else "0"
        raw_right = right_parts[index] if index < len(right_parts) else "0"
        try:
            left_num = int(raw_left)
            right_num = int(raw_right)
        except ValueError:
            if raw_left > raw_right:
                return 1
            if raw_left < raw_right:
                return -1
            continue
        if left_num > right_num:
            return 1
        if left_num < right_num:
            return -1
    return 0


class UpdateService:
    def __init__(
        self,
        *,
        current_version: str,
        config_service=None,
        manifest_url: str = UPDATE_MANIFEST_URL,
        signature_url: str = UPDATE_SIGNATURE_URL,
        release_feed_url: str = UPDATE_RELEASE_FEED_URL,
        release_tag_prefix: str = UPDATE_RELEASE_TAG_PREFIX,
        manifest_asset_name: str = UPDATE_MANIFEST_ASSET_NAME,
        signature_asset_name: str = UPDATE_SIGNATURE_ASSET_NAME,
        verify_key: str = UPDATE_VERIFY_KEY,
    ) -> None:
        self._current_version = current_version
        self._config_service = config_service
        self._manifest_url = manifest_url
        self._signature_url = signature_url
        self._release_feed_url = release_feed_url
        self._release_tag_prefix = release_tag_prefix.strip()
        self._manifest_asset_name = manifest_asset_name.strip() or "qt-latest.json"
        self._signature_asset_name = signature_asset_name.strip() or f"{self._manifest_asset_name}.sig"
        self._verify_key = verify_key.strip()

    def check_for_updates(self) -> UpdateInfo:
        if not self._manifest_url and not self._release_feed_url:
            raise RuntimeError("更新清单地址未配置")

        with self._client(timeout=20.0) as client:
            manifest_url, signature_url = self._resolve_manifest_endpoints(client)
            manifest_bytes = self._get_response(
                client,
                manifest_url,
                stage="下载更新清单失败",
            ).content
            signature_verified = self._verify_manifest(client, manifest_bytes, signature_url)

        payload = json.loads(manifest_bytes.decode("utf-8"))
        version = str(payload.get("version") or "")
        if not version:
            raise RuntimeError("更新清单缺少 version")

        platform = self._resolve_platform_payload(payload)
        download_url = str(platform.get("url") or "")
        sha256 = str(platform.get("sha256") or "").strip().lower()
        size = int(platform.get("size") or 0)
        notes = str(payload.get("notes") or "")
        pub_date = str(payload.get("pub_date") or "")
        available = compare_versions(version, self._current_version) > 0

        installable = bool(
            available
            and signature_verified
            and download_url
            and sha256
            and self.can_install_updates()
        )

        if not available:
            message = "当前已是最新版本"
        elif not signature_verified:
            message = f"发现新版本 v{version}，但更新清单未通过签名校验，请手动下载安装。"
        elif not self.can_install_updates():
            message = f"发现新版本 v{version}，当前环境仅支持手动下载安装。"
        else:
            message = f"发现新版本 v{version}"

        return UpdateInfo(
            available=available,
            version=version,
            notes=notes,
            pub_date=pub_date,
            installable=installable,
            manual_url=download_url,
            message=message,
            signature_verified=signature_verified,
            download_url=download_url,
            sha256=sha256,
            size=size,
        )

    def can_install_updates(self) -> bool:
        return sys.platform.startswith("win") and bool(getattr(sys, "frozen", False))

    def download_update(
        self,
        info: UpdateInfo,
        *,
        on_progress=None,
    ) -> DownloadedUpdate:
        if not info.download_url:
            raise RuntimeError("更新清单缺少安装包下载地址")
        if not info.sha256:
            raise RuntimeError("更新清单缺少安装包 SHA256")

        updates_dir = updates_root() / info.version
        updates_dir.mkdir(parents=True, exist_ok=True)
        installer_name = self._installer_name_from_url(info.download_url)
        installer_path = updates_dir / installer_name
        expected_size = int(info.size or 0)

        if installer_path.exists() and self._matches_digest(installer_path, info.sha256, expected_size):
            if on_progress:
                on_progress(installer_path.stat().st_size, installer_path.stat().st_size, True)
            return DownloadedUpdate(
                version=info.version,
                installer_path=installer_path,
                download_url=info.download_url,
                sha256=info.sha256,
                size=installer_path.stat().st_size,
            )

        temp_path = installer_path.with_suffix(f"{installer_path.suffix}.part")
        digest = hashlib.sha256()

        try:
            with self._client(timeout=120.0) as client:
                with self._stream_response(client, info.download_url, stage="下载安装包失败") as response:
                    total = int(response.headers.get("Content-Length") or expected_size or 0)
                    downloaded = 0

                    with temp_path.open("wb") as handle:
                        for chunk in response.iter_bytes(chunk_size=1024 * 256):
                            if not chunk:
                                continue
                            handle.write(chunk)
                            digest.update(chunk)
                            downloaded += len(chunk)
                            if on_progress:
                                on_progress(downloaded, total, False)
        except Exception:
            temp_path.unlink(missing_ok=True)
            raise

        actual_size = temp_path.stat().st_size
        actual_digest = digest.hexdigest().lower()
        if actual_digest != info.sha256.lower():
            temp_path.unlink(missing_ok=True)
            raise RuntimeError("更新安装包校验失败：SHA256 不匹配")
        if expected_size and actual_size != expected_size:
            temp_path.unlink(missing_ok=True)
            raise RuntimeError("更新安装包校验失败：文件大小不匹配")

        temp_path.replace(installer_path)
        if on_progress:
            on_progress(actual_size, actual_size, True)

        return DownloadedUpdate(
            version=info.version,
            installer_path=installer_path,
            download_url=info.download_url,
            sha256=info.sha256,
            size=actual_size,
        )

    def install_update(self, downloaded: DownloadedUpdate) -> None:
        if not self.can_install_updates():
            raise RuntimeError("当前环境不支持自动安装更新")

        installer_path = downloaded.installer_path.resolve()
        if not installer_path.exists():
            raise RuntimeError("更新安装包不存在")

        current_executable = Path(sys.executable).resolve()
        script_path = self._write_windows_update_script(
            installer_path=installer_path,
            app_executable=current_executable,
            target_pid=os.getpid(),
        )

        creationflags = 0
        if sys.platform.startswith("win"):
            creationflags = getattr(subprocess, "DETACHED_PROCESS", 0) | getattr(
                subprocess, "CREATE_NEW_PROCESS_GROUP", 0
            )

        subprocess.Popen(  # noqa: S603
            [
                "powershell",
                "-NoProfile",
                "-ExecutionPolicy",
                "Bypass",
                "-WindowStyle",
                "Hidden",
                "-File",
                str(script_path),
            ],
            creationflags=creationflags,
        )

    def _verify_manifest(
        self,
        client: "httpx.Client",
        manifest_bytes: bytes,
        signature_url: str,
    ) -> bool:
        if not self._verify_key:
            return False
        if not signature_url:
            raise RuntimeError("更新签名地址未配置")

        signature_response = self._get_response(
            client,
            signature_url,
            stage="下载更新签名失败",
        )
        signature_text = signature_response.text.strip()
        if not signature_text:
            raise RuntimeError("更新签名文件为空")

        try:
            from nacl.exceptions import BadSignatureError
            from nacl.signing import VerifyKey
        except ModuleNotFoundError as exc:
            raise self._missing_signature_dependency_error(exc, import_stage=True) from exc

        try:
            verify_key = VerifyKey(base64.b64decode(self._verify_key))
            verify_key.verify(manifest_bytes, base64.b64decode(signature_text))
        except ModuleNotFoundError as exc:
            raise self._missing_signature_dependency_error(exc, import_stage=False) from exc
        except (ValueError, BadSignatureError) as exc:
            raise RuntimeError(f"更新清单验签失败：{exc}") from exc

        return True

    def _missing_signature_dependency_error(
        self,
        exc: ModuleNotFoundError,
        *,
        import_stage: bool,
    ) -> RuntimeError:
        missing_name = str(exc.name or "").strip()
        if import_stage and missing_name in {"nacl", "nacl.exceptions", "nacl.signing"}:
            return RuntimeError("缺少 PyNaCl 依赖，无法校验更新签名")
        if not missing_name:
            missing_name = "未知模块"
        return RuntimeError(f"更新验签依赖缺失：{missing_name}")

    def _resolve_platform_payload(self, payload: dict) -> dict:
        platforms = payload.get("platforms") or {}
        platform_key = self._platform_key()
        target = platforms.get(platform_key)
        if not isinstance(target, dict):
            return {}
        return target

    def _platform_key(self) -> str:
        if sys.platform.startswith("win"):
            return "windows-x86_64"
        if sys.platform == "darwin":
            return "darwin-universal"
        return "linux-x86_64"

    def _client(self, *, timeout: float) -> "httpx.Client":
        try:
            import httpx
        except ModuleNotFoundError as exc:
            raise RuntimeError("缺少 httpx 依赖，无法检查更新") from exc

        kwargs: dict[str, object] = {
            "timeout": timeout,
            "follow_redirects": True,
            "headers": {
                "User-Agent": APP_NAME,
                "Accept": "application/json, application/vnd.github+json;q=0.9, */*;q=0.8",
            },
        }
        proxy = self._proxy()
        if proxy:
            kwargs["proxy"] = proxy
        return httpx.Client(**kwargs)

    def _resolve_manifest_endpoints(self, client: "httpx.Client") -> tuple[str, str]:
        if self._release_feed_url:
            response = self._get_response(
                client,
                self._release_feed_url,
                stage="获取 Qt 发布列表失败",
            )
            return self._select_release_assets(response.json())
        if not self._manifest_url:
            raise RuntimeError("更新清单地址未配置")
        return self._manifest_url, self._signature_url

    def _get_response(self, client: "httpx.Client", url: str, *, stage: str) -> "httpx.Response":
        try:
            response = client.get(url)
            response.raise_for_status()
            return response
        except Exception as exc:
            if self._is_http_error(exc):
                raise self._wrap_http_error(stage, exc) from exc
            raise

    @contextmanager
    def _stream_response(self, client: "httpx.Client", url: str, *, stage: str):
        try:
            with client.stream("GET", url) as response:
                response.raise_for_status()
                yield response
        except Exception as exc:
            if self._is_http_error(exc):
                raise self._wrap_http_error(stage, exc) from exc
            raise

    def _wrap_http_error(self, stage: str, exc: Exception) -> RuntimeError:
        detail = self._http_error_detail(exc)
        return RuntimeError(f"{stage}：{detail}" if detail else stage)

    def _http_error_detail(self, exc: Exception) -> str:
        try:
            import httpx
        except ModuleNotFoundError:
            return str(exc).strip()

        if isinstance(exc, httpx.HTTPStatusError):
            status_code = exc.response.status_code
            reason = str(exc.response.reason_phrase or "").strip()
            return f"HTTP {status_code}{(' ' + reason) if reason else ''}"

        if isinstance(exc, httpx.RequestError):
            message = str(exc.args[0] if exc.args else exc).strip()
            return " ".join(message.split())

        return " ".join(str(exc).strip().split())

    def _is_http_error(self, exc: Exception) -> bool:
        try:
            import httpx
        except ModuleNotFoundError:
            return False
        return isinstance(exc, httpx.HTTPError)

    def _select_release_assets(self, releases_payload: object) -> tuple[str, str]:
        releases = releases_payload if isinstance(releases_payload, list) else []
        matched_release = False
        for release in releases:
            if not isinstance(release, dict):
                continue
            if release.get("draft"):
                continue

            tag_name = str(release.get("tag_name") or "")
            if self._release_tag_prefix and not tag_name.startswith(self._release_tag_prefix):
                continue

            matched_release = True
            assets = release.get("assets") or []
            manifest_url = self._release_asset_url(assets, self._manifest_asset_name)
            signature_url = self._release_asset_url(assets, self._signature_asset_name)
            if manifest_url and signature_url:
                return manifest_url, signature_url

        if matched_release:
            raise RuntimeError(
                f"最新 Qt 发布缺少 {self._manifest_asset_name} 或 {self._signature_asset_name} 资产"
            )
        if self._release_tag_prefix:
            raise RuntimeError(f"未找到 tag 前缀为 {self._release_tag_prefix} 的可用发布")
        raise RuntimeError("未找到可用的 Qt 发布")

    def _release_asset_url(self, assets: object, target_name: str) -> str:
        if not isinstance(assets, list):
            return ""
        for asset in assets:
            if not isinstance(asset, dict):
                continue
            if str(asset.get("name") or "").strip() != target_name:
                continue
            return str(asset.get("browser_download_url") or "").strip()
        return ""

    def _proxy(self) -> str | None:
        if not self._config_service:
            return None
        config = self._config_service.config
        if config.proxy.enabled and config.proxy.url.strip():
            return config.proxy.url.strip()
        return None

    def _installer_name_from_url(self, url: str) -> str:
        parsed = urlparse(url)
        candidate = Path(parsed.path).name.strip()
        return candidate or "mistrelay-desktop-qt-setup.exe"

    def _matches_digest(self, path: Path, expected_digest: str, expected_size: int) -> bool:
        if expected_size and path.stat().st_size != expected_size:
            return False

        digest = hashlib.sha256()
        with path.open("rb") as handle:
            while True:
                chunk = handle.read(1024 * 256)
                if not chunk:
                    break
                digest.update(chunk)
        return digest.hexdigest().lower() == expected_digest.lower()

    def _write_windows_update_script(
        self,
        *,
        installer_path: Path,
        app_executable: Path,
        target_pid: int,
    ) -> Path:
        temp_dir = Path(tempfile.mkdtemp(prefix="mistrelay-qt-update-"))
        script_path = temp_dir / "install-update.ps1"
        script_path.write_text(
            "\n".join(
                [
                    "$ErrorActionPreference = 'Stop'",
                    f"$targetPid = {target_pid}",
                    f"$installer = '{self._ps_literal(installer_path)}'",
                    f"$appExe = '{self._ps_literal(app_executable)}'",
                    "try { Wait-Process -Id $targetPid -ErrorAction SilentlyContinue } catch { }",
                    "$installerProcess = Start-Process -FilePath $installer -ArgumentList '/S' -PassThru -Wait",
                    "if ($installerProcess.ExitCode -ne 0) { exit $installerProcess.ExitCode }",
                    "Start-Sleep -Seconds 2",
                    "if (Test-Path $appExe) { Start-Process -FilePath $appExe }",
                ]
            )
            + "\n",
            encoding="utf-8",
        )
        return script_path

    def _ps_literal(self, value: Path) -> str:
        return str(value).replace("'", "''")
