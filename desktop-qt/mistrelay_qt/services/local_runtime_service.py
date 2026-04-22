from __future__ import annotations

import json
import os
import subprocess
import threading
import time
from dataclasses import dataclass, field
from http import HTTPStatus
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from itertools import count
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlparse

import httpx
from PySide6.QtCore import QObject, QUrl, Signal
from PySide6.QtGui import QDesktopServices
from PySide6.QtWidgets import QFileDialog

from ..constants import (
    DEFAULT_DOWNLOAD_DIRNAME,
    MIN_THREADS_PER_DOWNLOAD,
    PREVIEW_READY_BYTES,
    TRANSFER_PROGRESS_EMIT_INTERVAL,
)
from ..paths import preview_cache_root


class TransferCancelledError(RuntimeError):
    pass


@dataclass(slots=True)
class TransferProgress:
    downloaded_bytes: int = 0
    total_bytes: int | None = None
    download_speed: float = 0.0
    complete: bool = False
    cancelled: bool = False
    ready_for_preview: bool = False
    error: str = ""
    last_speed_sample_bytes: int = 0
    last_speed_sample_at: float | None = None
    last_emit_at: float = 0.0


@dataclass(slots=True)
class TransferHandle:
    transfer_id: str
    file_name: str
    source_url: str
    remote: str
    remote_path: str
    local_path: Path
    kind: str
    complete_marker_path: Path | None = None
    progress: TransferProgress = field(default_factory=TransferProgress)
    cancel_requested: threading.Event = field(default_factory=threading.Event)
    condition: threading.Condition = field(default_factory=threading.Condition)
    worker: threading.Thread | None = None
    requested_threads: int = 1


class ConcurrencyLimiter:
    def __init__(self, max_active: int) -> None:
        self._active = 0
        self._max_active = max(1, max_active)
        self._condition = threading.Condition()

    def update_max(self, max_active: int) -> None:
        with self._condition:
            self._max_active = max(1, max_active)
            self._condition.notify_all()

    def acquire(self) -> None:
        with self._condition:
            while self._active >= self._max_active:
                self._condition.wait()
            self._active += 1

    def release(self) -> None:
        with self._condition:
            self._active = max(0, self._active - 1)
            self._condition.notify_all()


class PreviewRequestHandler(BaseHTTPRequestHandler):
    server_version = "MistRelayQtPreview/1.0"

    def do_GET(self) -> None:  # noqa: N802
        service = self.server.runtime_service  # type: ignore[attr-defined]
        transfer_id = self.path.split("/preview/", 1)[-1].split("?", 1)[0]
        if not transfer_id or transfer_id == self.path:
            self.send_error(HTTPStatus.NOT_FOUND, "preview session not found")
            return

        handle = service.get_preview_handle(transfer_id)
        if handle is None:
            self.send_error(HTTPStatus.NOT_FOUND, "preview session not found")
            return

        try:
            self._serve_preview_file(service, handle)
        except TransferCancelledError:
            self.send_error(HTTPStatus.GONE, "preview cancelled")
        except FileNotFoundError:
            self.send_error(HTTPStatus.NOT_FOUND, "preview file not found")
        except Exception as exc:  # pragma: no cover - depends on runtime network/filesystem
            self.send_error(HTTPStatus.INTERNAL_SERVER_ERROR, str(exc))

    def _serve_preview_file(self, service: "LocalRuntimeService", handle: TransferHandle) -> None:
        snapshot = service.wait_for_available_bytes(handle.transfer_id, 1)
        total_bytes = snapshot["totalBytes"] or snapshot["downloadedBytes"]
        if not total_bytes:
            raise RuntimeError("preview file is empty")

        range_header = self.headers.get("Range")
        if range_header:
            start, end = service.parse_range_header(range_header, total_bytes)
            if start >= total_bytes:
                self.send_response(HTTPStatus.REQUESTED_RANGE_NOT_SATISFIABLE)
                self.send_header("Content-Range", f"bytes */{total_bytes}")
                self.end_headers()
                return
        else:
            start, end = 0, total_bytes - 1

        snapshot = service.wait_for_available_bytes(handle.transfer_id, start + 1)
        downloaded = int(snapshot["downloadedBytes"])
        available_end = total_bytes - 1 if snapshot["state"] == "completed" else max(start, downloaded - 1)
        end = min(end, available_end)
        length = max(0, end - start + 1)

        status = HTTPStatus.PARTIAL_CONTENT if range_header else HTTPStatus.OK
        self.send_response(status)
        self.send_header("Accept-Ranges", "bytes")
        self.send_header("Content-Type", service.guess_content_type(handle.file_name))
        self.send_header("Content-Length", str(length))
        if range_header:
            self.send_header("Content-Range", f"bytes {start}-{end}/{total_bytes}")
        self.end_headers()

        with handle.local_path.open("rb") as file_pointer:
            position = start
            remaining = length
            while remaining > 0:
                needed = position + min(remaining, 64 * 1024)
                snapshot = service.wait_for_available_bytes(handle.transfer_id, needed)
                available = int(snapshot["downloadedBytes"])
                if available <= position and snapshot["state"] != "completed":
                    continue

                chunk_size = min(remaining, max(0, available - position))
                if chunk_size <= 0:
                    break

                file_pointer.seek(position)
                payload = file_pointer.read(chunk_size)
                if not payload:
                    break

                self.wfile.write(payload)
                position += len(payload)
                remaining -= len(payload)

    def log_message(self, format: str, *args: object) -> None:  # noqa: A003
        return


class LocalRuntimeService(QObject):
    transferUpdated = Signal(dict)

    def __init__(self, config_service=None) -> None:
        super().__init__()
        self._config_service = config_service
        self._transfer_counter = count(1)
        self._download_sessions: dict[str, TransferHandle] = {}
        self._preview_sessions: dict[str, TransferHandle] = {}
        self._limiter = ConcurrencyLimiter(self._configured_max_concurrent())
        self._preview_server: ThreadingHTTPServer | None = None
        self._preview_server_thread: threading.Thread | None = None
        if os.getenv("MISTRELAY_DISABLE_PREVIEW_SERVER") != "1":
            try:
                self._preview_server = ThreadingHTTPServer(("127.0.0.1", 0), PreviewRequestHandler)
                self._preview_server.runtime_service = self  # type: ignore[attr-defined]
                self._preview_server_thread = threading.Thread(
                    target=self._preview_server.serve_forever,
                    daemon=True,
                )
                self._preview_server_thread.start()
            except OSError:
                self._preview_server = None

    def shutdown(self) -> None:
        if self._preview_server is not None:
            self._preview_server.shutdown()

    def get_default_download_dir(self) -> str:
        return str(Path.home() / DEFAULT_DOWNLOAD_DIRNAME / "MistRelay")

    def pick_download_dir(self, current_dir: str = "") -> str:
        base_dir = current_dir or self.get_default_download_dir()
        selected = QFileDialog.getExistingDirectory(None, "选择下载目录", base_dir)
        return selected or current_dir

    def open_local_file(self, local_path: str) -> None:
        QDesktopServices.openUrl(QUrl.fromLocalFile(local_path))

    def show_local_file_in_folder(self, local_path: str) -> None:
        if os.name == "nt":
            subprocess.Popen(["explorer", f"/select,{local_path}"])  # noqa: S603,S607
            return
        QDesktopServices.openUrl(QUrl.fromLocalFile(str(Path(local_path).parent)))

    def open_external_url(self, url: str) -> None:
        QDesktopServices.openUrl(QUrl(url))

    def list_download_statuses(self) -> list[dict[str, Any]]:
        return [self._snapshot(handle) for handle in self._download_sessions.values()]

    def start_download(
        self,
        *,
        source_url: str,
        remote: str,
        remote_path: str,
        file_name: str,
    ) -> dict[str, Any]:
        existing_handle = self._find_existing_download(remote=remote, remote_path=remote_path, source_url=source_url)
        if existing_handle is not None:
            snapshot = self._snapshot(existing_handle)
            snapshot["existing"] = True
            return snapshot

        destination = self._resolve_transfer_destination(
            self._downloads_root_dir(),
            remote,
            remote_path,
            file_name,
            source_url,
        )
        transfer_id = self._new_transfer_id()
        handle = TransferHandle(
            transfer_id=transfer_id,
            file_name=file_name,
            source_url=source_url,
            remote=remote,
            remote_path=remote_path,
            local_path=destination,
            kind="download",
            requested_threads=self._configured_threads_per_download(),
        )
        self._download_sessions[transfer_id] = handle
        self._emit_snapshot(handle, force=True)
        self._start_worker(handle, use_limiter=True)
        snapshot = self._snapshot(handle)
        snapshot["existing"] = False
        return snapshot

    def prepare_preview_file(
        self,
        *,
        source_url: str,
        remote: str,
        remote_path: str,
        file_name: str,
    ) -> dict[str, Any]:
        destination = self._resolve_transfer_destination(
            preview_cache_root(),
            remote,
            remote_path,
            file_name,
            source_url,
        )
        marker = self._complete_marker_path(destination)
        if destination.exists() and marker.exists():
            return {
                "fileName": file_name,
                "localPath": str(destination),
            }

        self._download_direct(source_url, destination, write_sidecar=False)
        marker.write_text("ok", encoding="utf-8")
        return {
            "fileName": file_name,
            "localPath": str(destination),
        }

    def start_preview_stream(
        self,
        *,
        source_url: str,
        remote: str,
        remote_path: str,
        file_name: str,
    ) -> dict[str, Any]:
        if self._preview_server is None:
            raise RuntimeError("当前环境无法启动本地预览服务")
        destination = self._resolve_transfer_destination(
            preview_cache_root(),
            remote,
            remote_path,
            file_name,
            source_url,
        )
        marker = self._complete_marker_path(destination)
        transfer_id = self._new_transfer_id()
        handle = TransferHandle(
            transfer_id=transfer_id,
            file_name=file_name,
            source_url=source_url,
            remote=remote,
            remote_path=remote_path,
            local_path=destination,
            kind="preview",
            complete_marker_path=marker,
            requested_threads=1,
        )

        if destination.exists() and marker.exists():
            size = destination.stat().st_size
            handle.progress.downloaded_bytes = size
            handle.progress.total_bytes = size
            handle.progress.complete = True
            handle.progress.ready_for_preview = True

        self._preview_sessions[transfer_id] = handle
        self._emit_snapshot(handle, force=True)
        if not handle.progress.complete:
            self._start_worker(handle, use_limiter=False)

        return {
            "transferId": transfer_id,
            "streamUrl": self._preview_stream_url(transfer_id),
            "localPath": str(destination),
            "readyForPreview": handle.progress.ready_for_preview,
        }

    def get_transfer_status(self, transfer_id: str) -> dict[str, Any]:
        handle = self._lookup_transfer(transfer_id)
        if handle is None:
            raise RuntimeError("未找到桌面传输任务")
        return self._snapshot(handle)

    def cancel_download(self, transfer_id: str) -> dict[str, Any]:
        handle = self._download_sessions.get(transfer_id)
        if handle is None:
            raise RuntimeError("未找到本地下载任务")
        handle.cancel_requested.set()
        with handle.condition:
            handle.condition.notify_all()
        self._emit_snapshot(handle, force=True)
        return self._snapshot(handle)

    def retry_download(self, transfer_id: str) -> dict[str, Any]:
        handle = self._download_sessions.get(transfer_id)
        if handle is None:
            raise RuntimeError("未找到本地下载任务")

        snapshot = self._snapshot(handle)
        if snapshot["state"] == "completed":
            raise RuntimeError("已完成任务无需重试")
        if snapshot["state"] == "cancelling":
            raise RuntimeError("任务仍在取消中，请稍后重试")
        if snapshot["state"] not in {"error", "cancelled"}:
            raise RuntimeError("只有失败或已取消任务可以重试")

        self._cleanup_transfer_artifacts(handle)
        handle.cancel_requested.clear()
        handle.progress = TransferProgress()
        self._emit_snapshot(handle, force=True)
        self._start_worker(handle, use_limiter=True)
        return self._snapshot(handle)

    def remove_download_session(self, transfer_id: str) -> None:
        handle = self._download_sessions.get(transfer_id)
        if handle is None:
            raise RuntimeError("未找到本地下载任务")
        state = self._snapshot(handle)["state"]
        if state not in {"completed", "error", "cancelled"}:
            raise RuntimeError("只有已结束任务可以删除")
        self._download_sessions.pop(transfer_id, None)

    def cancel_preview(self, transfer_id: str) -> None:
        handle = self._preview_sessions.pop(transfer_id, None)
        if handle is None:
            raise RuntimeError("未找到本地预览任务")
        if self._snapshot(handle)["state"] not in {"completed", "error", "cancelled"}:
            handle.cancel_requested.set()
            with handle.condition:
                handle.condition.notify_all()

    def get_preview_handle(self, transfer_id: str) -> TransferHandle | None:
        return self._preview_sessions.get(transfer_id)

    def wait_for_available_bytes(self, transfer_id: str, needed_bytes: int) -> dict[str, Any]:
        handle = self.get_preview_handle(transfer_id)
        if handle is None:
            raise FileNotFoundError("preview session not found")

        with handle.condition:
            while True:
                snapshot = self._snapshot_locked(handle)
                if snapshot["state"] == "cancelled":
                    raise TransferCancelledError("传输已取消")
                if snapshot["state"] == "error":
                    raise RuntimeError(snapshot["error"] or "预览缓存失败")
                if snapshot["state"] == "completed" or int(snapshot["downloadedBytes"]) >= needed_bytes:
                    return snapshot
                handle.condition.wait()

    def parse_range_header(self, value: str, total_bytes: int) -> tuple[int, int]:
        if not value.startswith("bytes="):
            return 0, total_bytes - 1
        start_raw, _, end_raw = value.removeprefix("bytes=").partition("-")
        try:
            start = int(start_raw) if start_raw else 0
        except ValueError:
            start = 0
        try:
            end = int(end_raw) if end_raw else total_bytes - 1
        except ValueError:
            end = total_bytes - 1
        if end < start:
            end = total_bytes - 1
        return start, end

    def guess_content_type(self, file_name: str) -> str:
        suffix = Path(file_name).suffix.lower()
        if suffix in {".mp4", ".m4v"}:
            return "video/mp4"
        if suffix == ".webm":
            return "video/webm"
        if suffix == ".mkv":
            return "video/x-matroska"
        if suffix in {".jpg", ".jpeg"}:
            return "image/jpeg"
        if suffix == ".png":
            return "image/png"
        if suffix == ".gif":
            return "image/gif"
        return "application/octet-stream"

    def _configured_proxy(self) -> str | None:
        if not self._config_service:
            return None
        config = self._config_service.config
        if config.proxy.enabled and config.proxy.url.strip():
            return config.proxy.url.strip()
        return None

    def _configured_threads_per_download(self) -> int:
        if not self._config_service:
            return 4
        return max(MIN_THREADS_PER_DOWNLOAD, int(self._config_service.config.download.threads_per_download))

    def _configured_max_concurrent(self) -> int:
        if not self._config_service:
            return 3
        return max(1, int(self._config_service.config.download.max_concurrent_downloads))

    def _new_transfer_id(self) -> str:
        return f"{os.getpid()}-{next(self._transfer_counter)}"

    def _downloads_root_dir(self) -> Path:
        if not self._config_service:
            return Path(self.get_default_download_dir())
        raw = self._config_service.config.download.download_dir.strip()
        return Path(raw) if raw else Path(self.get_default_download_dir())

    def _preview_stream_url(self, transfer_id: str) -> str:
        if self._preview_server is None:
            raise RuntimeError("本地预览服务不可用")
        port = self._preview_server.server_address[1]
        return f"http://127.0.0.1:{port}/preview/{transfer_id}"

    def _lookup_transfer(self, transfer_id: str) -> TransferHandle | None:
        return self._preview_sessions.get(transfer_id) or self._download_sessions.get(transfer_id)

    def _find_existing_download(
        self,
        *,
        remote: str,
        remote_path: str,
        source_url: str,
    ) -> TransferHandle | None:
        for handle in self._download_sessions.values():
            if handle.remote != remote or handle.remote_path != remote_path or handle.source_url != source_url:
                continue
            if self._snapshot(handle)["state"] in {"error", "cancelled"}:
                continue
            return handle
        return None

    def _start_worker(self, handle: TransferHandle, *, use_limiter: bool) -> None:
        if handle.worker and handle.worker.is_alive():
            return

        handle.worker = threading.Thread(
            target=self._run_transfer,
            args=(handle, use_limiter),
            daemon=True,
        )
        handle.worker.start()

    def _run_transfer(self, handle: TransferHandle, use_limiter: bool) -> None:
        if use_limiter:
            self._limiter.update_max(self._configured_max_concurrent())
            self._limiter.acquire()

        try:
            self._abort_if_cancelled(handle)
            if handle.kind == "download" and handle.requested_threads >= MIN_THREADS_PER_DOWNLOAD:
                self._multi_thread_download(handle)
            else:
                self._stream_transfer(handle)
            self._mark_completed(handle)
        except TransferCancelledError:
            self._mark_cancelled(handle)
        except Exception as exc:  # pragma: no cover - depends on runtime network/filesystem
            self._mark_failed(handle, str(exc))
        finally:
            if use_limiter:
                self._limiter.release()

    def _stream_transfer(self, handle: TransferHandle) -> None:
        self._ensure_parent_dir(handle.local_path)
        self._abort_if_cancelled(handle)

        if handle.kind == "preview" and handle.complete_marker_path and handle.complete_marker_path.exists() and handle.local_path.exists():
            size = handle.local_path.stat().st_size
            with handle.condition:
                handle.progress.downloaded_bytes = size
                handle.progress.total_bytes = size
                handle.progress.complete = True
                handle.progress.ready_for_preview = True
                handle.condition.notify_all()
            return

        if handle.kind == "preview":
            self._cleanup_transfer_artifacts(handle)
            target_path = handle.local_path
        else:
            target_path = self._temporary_download_path(handle.local_path)
            if target_path.exists():
                target_path.unlink()

        with self._build_http_client() as client:
            with client.stream("GET", handle.source_url, follow_redirects=True) as response:
                if response.status_code not in {HTTPStatus.OK, HTTPStatus.PARTIAL_CONTENT}:
                    raise RuntimeError(f"下载文件失败: 服务返回 {response.status_code}")

                total_bytes = response.headers.get("Content-Length")
                total = int(total_bytes) if total_bytes and total_bytes.isdigit() else None
                with handle.condition:
                    handle.progress.total_bytes = total
                    handle.progress.ready_for_preview = False
                    handle.condition.notify_all()

                with target_path.open("wb") as file_pointer:
                    for chunk in response.iter_bytes(chunk_size=64 * 1024):
                        self._abort_if_cancelled(handle)
                        if not chunk:
                            continue
                        file_pointer.write(chunk)
                        if handle.kind == "preview":
                            file_pointer.flush()
                        self._advance_progress(handle, len(chunk))

        if handle.kind == "download":
            self._finalize_download_target(handle, target_path)
        else:
            if handle.complete_marker_path:
                handle.complete_marker_path.write_text("ok", encoding="utf-8")

    def _multi_thread_download(self, handle: TransferHandle) -> None:
        probe = self._probe_download(handle.source_url)
        if not probe["supports_ranges"] or not probe["total_bytes"] or probe["total_bytes"] < 2 * 1024 * 1024:
            self._stream_transfer(handle)
            return

        total_bytes = int(probe["total_bytes"])
        threads = min(handle.requested_threads, max(MIN_THREADS_PER_DOWNLOAD, total_bytes // (512 * 1024)))
        if threads < MIN_THREADS_PER_DOWNLOAD:
            self._stream_transfer(handle)
            return

        self._ensure_parent_dir(handle.local_path)
        target_path = self._temporary_download_path(handle.local_path)
        if target_path.exists():
            target_path.unlink()
        with target_path.open("wb") as file_pointer:
            file_pointer.truncate(total_bytes)

        with handle.condition:
            handle.progress.total_bytes = total_bytes
            handle.progress.ready_for_preview = False
            handle.condition.notify_all()

        segment_size = total_bytes // threads
        workers: list[threading.Thread] = []
        errors: list[str] = []
        errors_lock = threading.Lock()

        def worker(segment_start: int, segment_end: int) -> None:
            try:
                self._download_range(handle, target_path, segment_start, segment_end)
            except TransferCancelledError:
                handle.cancel_requested.set()
            except Exception as exc:  # pragma: no cover - runtime network dependent
                with errors_lock:
                    errors.append(str(exc))
                handle.cancel_requested.set()
                with handle.condition:
                    handle.condition.notify_all()

        for index in range(threads):
            start = index * segment_size
            end = total_bytes - 1 if index == threads - 1 else ((index + 1) * segment_size) - 1
            thread = threading.Thread(target=worker, args=(start, end), daemon=True)
            workers.append(thread)
            thread.start()

        for thread in workers:
            thread.join()

        if handle.cancel_requested.is_set():
            self._cleanup_file(target_path)
            if errors:
                raise RuntimeError(errors[0])
            raise TransferCancelledError("传输已取消")

        if errors:
            self._cleanup_file(target_path)
            raise RuntimeError(errors[0])

        self._finalize_download_target(handle, target_path)

    def _download_range(self, handle: TransferHandle, target_path: Path, start: int, end: int) -> None:
        headers = {"Range": f"bytes={start}-{end}"}
        with self._build_http_client() as client:
            with client.stream("GET", handle.source_url, headers=headers, follow_redirects=True) as response:
                if response.status_code not in {HTTPStatus.PARTIAL_CONTENT, HTTPStatus.OK}:
                    raise RuntimeError(f"分片下载失败: 服务返回 {response.status_code}")

                position = start
                with target_path.open("r+b") as file_pointer:
                    file_pointer.seek(start)
                    for chunk in response.iter_bytes(chunk_size=64 * 1024):
                        self._abort_if_cancelled(handle)
                        if not chunk:
                            continue
                        file_pointer.seek(position)
                        file_pointer.write(chunk)
                        position += len(chunk)
                        self._advance_progress(handle, len(chunk))

    def _build_http_client(self) -> httpx.Client:
        kwargs: dict[str, Any] = {
            "timeout": 60 * 60,
            "follow_redirects": True,
            "headers": {"User-Agent": "MistRelay Desktop Qt"},
        }
        proxy = self._configured_proxy()
        if proxy:
            kwargs["proxy"] = proxy
        return httpx.Client(**kwargs)

    def _probe_download(self, source_url: str) -> dict[str, Any]:
        with self._build_http_client() as client:
            response = client.head(source_url)
            supports_ranges = response.headers.get("Accept-Ranges", "").lower() == "bytes"
            total_raw = response.headers.get("Content-Length")
            total_bytes = int(total_raw) if total_raw and total_raw.isdigit() else None
            return {
                "supports_ranges": supports_ranges,
                "total_bytes": total_bytes,
            }

    def _download_direct(self, source_url: str, destination: Path, *, write_sidecar: bool) -> None:
        self._ensure_parent_dir(destination)
        temp_path = self._temporary_download_path(destination)
        if temp_path.exists():
            temp_path.unlink()

        with self._build_http_client() as client:
            with client.stream("GET", source_url, follow_redirects=True) as response:
                if response.status_code not in {HTTPStatus.OK, HTTPStatus.PARTIAL_CONTENT}:
                    raise RuntimeError(f"下载文件失败: 服务返回 {response.status_code}")
                with temp_path.open("wb") as file_pointer:
                    for chunk in response.iter_bytes(chunk_size=64 * 1024):
                        if not chunk:
                            continue
                        file_pointer.write(chunk)

        if destination.exists():
            destination.unlink()
        temp_path.replace(destination)
        if write_sidecar:
            self._write_telegram_identity(destination, source_url)

    def _finalize_download_target(self, handle: TransferHandle, temp_path: Path) -> None:
        if handle.local_path.exists():
            handle.local_path.unlink()
        temp_path.replace(handle.local_path)
        self._write_telegram_identity(handle.local_path, handle.source_url)

    def _abort_if_cancelled(self, handle: TransferHandle) -> None:
        if handle.cancel_requested.is_set():
            raise TransferCancelledError("传输已取消")

    def _advance_progress(self, handle: TransferHandle, delta: int) -> None:
        with handle.condition:
            progress = handle.progress
            progress.downloaded_bytes += delta
            now = time.monotonic()
            if progress.last_speed_sample_at is None:
                progress.last_speed_sample_at = now
                progress.last_speed_sample_bytes = progress.downloaded_bytes
            else:
                elapsed = now - progress.last_speed_sample_at
                if elapsed >= 0.25:
                    progress.download_speed = (
                        progress.downloaded_bytes - progress.last_speed_sample_bytes
                    ) / max(elapsed, 0.001)
                    progress.last_speed_sample_bytes = progress.downloaded_bytes
                    progress.last_speed_sample_at = now
            progress.ready_for_preview = handle.kind == "preview" and (
                progress.complete or progress.downloaded_bytes >= self._preview_ready_threshold(progress.total_bytes)
            )
            handle.condition.notify_all()

        self._emit_snapshot(handle)

    def _mark_completed(self, handle: TransferHandle) -> None:
        with handle.condition:
            progress = handle.progress
            if progress.total_bytes is None and handle.local_path.exists():
                progress.total_bytes = handle.local_path.stat().st_size
            if handle.local_path.exists():
                progress.downloaded_bytes = handle.local_path.stat().st_size
            progress.complete = True
            progress.cancelled = False
            progress.error = ""
            progress.ready_for_preview = handle.kind == "preview"
            progress.download_speed = 0.0
            handle.condition.notify_all()
        self._emit_snapshot(handle, force=True)

    def _mark_failed(self, handle: TransferHandle, message: str) -> None:
        with handle.condition:
            progress = handle.progress
            progress.complete = False
            progress.cancelled = False
            progress.ready_for_preview = False
            progress.error = message
            progress.download_speed = 0.0
            handle.condition.notify_all()
        self._emit_snapshot(handle, force=True)

    def _mark_cancelled(self, handle: TransferHandle) -> None:
        self._cleanup_transfer_artifacts(handle)
        with handle.condition:
            progress = handle.progress
            progress.complete = False
            progress.cancelled = True
            progress.ready_for_preview = False
            progress.error = ""
            progress.download_speed = 0.0
            handle.condition.notify_all()
        self._emit_snapshot(handle, force=True)

    def _emit_snapshot(self, handle: TransferHandle, *, force: bool = False) -> None:
        with handle.condition:
            now = time.monotonic()
            if not force and now - handle.progress.last_emit_at < TRANSFER_PROGRESS_EMIT_INTERVAL:
                return
            handle.progress.last_emit_at = now
            snapshot = self._snapshot_locked(handle)
        self.transferUpdated.emit(snapshot)

    def _snapshot(self, handle: TransferHandle) -> dict[str, Any]:
        with handle.condition:
            return self._snapshot_locked(handle)

    def _snapshot_locked(self, handle: TransferHandle) -> dict[str, Any]:
        progress = handle.progress
        total = progress.total_bytes
        if progress.cancelled:
            state = "cancelled"
        elif handle.cancel_requested.is_set() and not progress.error and not progress.complete:
            state = "cancelling"
        elif progress.error:
            state = "error"
        elif progress.complete:
            state = "completed"
        elif progress.ready_for_preview:
            state = "ready"
        elif progress.downloaded_bytes > 0:
            state = "downloading"
        else:
            state = "pending"

        progress_percent = 0.0
        if total and total > 0:
            progress_percent = min(100.0, (progress.downloaded_bytes / total) * 100.0)

        return {
            "transferId": handle.transfer_id,
            "fileName": handle.file_name,
            "remote": handle.remote,
            "remotePath": handle.remote_path,
            "sourceUrl": handle.source_url,
            "kind": handle.kind,
            "localPath": str(handle.local_path),
            "downloadedBytes": progress.downloaded_bytes,
            "totalBytes": total,
            "downloadSpeed": int(progress.download_speed),
            "progressPercent": round(progress_percent, 2),
            "state": state,
            "readyForPreview": progress.ready_for_preview,
            "error": progress.error,
        }

    def _ensure_parent_dir(self, path: Path) -> None:
        path.parent.mkdir(parents=True, exist_ok=True)

    def _cleanup_transfer_artifacts(self, handle: TransferHandle) -> None:
        self._cleanup_file(handle.local_path)
        self._cleanup_file(self._temporary_download_path(handle.local_path))
        if handle.complete_marker_path:
            self._cleanup_file(handle.complete_marker_path)
        sidecar = self._telegram_identity_sidecar_path(handle.local_path)
        self._cleanup_file(sidecar)

    def _cleanup_file(self, path: Path | None) -> None:
        if path and path.exists():
            path.unlink()

    def _temporary_download_path(self, destination: Path) -> Path:
        suffix = destination.suffix
        return destination.with_suffix(f"{suffix}.download" if suffix else ".download")

    def _complete_marker_path(self, local_path: Path) -> Path:
        return Path(f"{local_path}.complete")

    def _preview_ready_threshold(self, total_bytes: int | None) -> int:
        if total_bytes is None:
            return PREVIEW_READY_BYTES
        return max(512 * 1024, min(total_bytes, PREVIEW_READY_BYTES))

    def _sanitize_path_component(self, value: str) -> str:
        sanitized = "".join(
            "_" if char in '<>:"/\\|?*' or ord(char) < 32 else char
            for char in value
        ).strip().strip(".")
        return sanitized or "_"

    def _build_relative_file_path(self, remote: str, remote_path: str, file_name: str) -> Path:
        relative = Path(self._sanitize_path_component(remote))
        if remote.lower() == "telegram" or remote_path.startswith("tg://"):
            return relative / self._sanitize_path_component(file_name)

        current = relative
        for part in Path(remote_path).parts:
            if part in {"", ".", "..", "/"}:
                continue
            current /= self._sanitize_path_component(part)

        if not current.name:
            current /= self._sanitize_path_component(file_name)
        return current

    def _resolve_transfer_destination(
        self,
        root_dir: Path,
        remote: str,
        remote_path: str,
        file_name: str,
        source_url: str,
    ) -> Path:
        if remote.lower() == "telegram" or remote_path.startswith("tg://"):
            return self._resolve_telegram_destination(root_dir, file_name, source_url)
        return root_dir / self._build_relative_file_path(remote, remote_path, file_name)

    def _resolve_telegram_destination(self, root_dir: Path, file_name: str, source_url: str) -> Path:
        telegram_root = root_dir / "telegram"
        telegram_root.mkdir(parents=True, exist_ok=True)
        sanitized = self._sanitize_path_component(file_name)
        preferred = telegram_root / sanitized
        source_hash = self._extract_telegram_source_hash(source_url)
        if not source_hash:
            return preferred

        stem = preferred.stem or sanitized
        suffix = preferred.suffix
        counter = 1
        while True:
            candidate = preferred if counter == 1 else telegram_root / f"{stem} ({counter}){suffix}"
            if not candidate.exists():
                return candidate
            identity = self._read_telegram_identity(candidate)
            if identity and identity.get("source_hash") == source_hash:
                return candidate
            counter += 1

    def _telegram_identity_sidecar_path(self, destination: Path) -> Path:
        file_name = destination.name or "download"
        return destination.with_name(f"{file_name}.mistrelay.json")

    def _extract_telegram_source_hash(self, source_url: str) -> str | None:
        parsed = urlparse(source_url)
        for key, value in parse_qsl(parsed.query):
            if key == "hash" and value.strip():
                return value
        return None

    def _read_telegram_identity(self, destination: Path) -> dict[str, Any] | None:
        sidecar = self._telegram_identity_sidecar_path(destination)
        if not sidecar.exists():
            return None
        try:
            return json.loads(sidecar.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            return None

    def _write_telegram_identity(self, destination: Path, source_url: str) -> None:
        source_hash = self._extract_telegram_source_hash(source_url)
        if not source_hash:
            return
        sidecar = self._telegram_identity_sidecar_path(destination)
        sidecar.write_text(
            json.dumps({"source_hash": source_hash}, ensure_ascii=False),
            encoding="utf-8",
        )
