from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, QTimer, Signal, Slot

from ..formatters import format_bytes, format_datetime, format_progress, format_speed
from ..list_models import RoleListModel
from ..task_runner import TaskRunner
from .base import BaseViewModel


class DownloadsViewModel(BaseViewModel):
    summaryCardsChanged = Signal()
    currentTabChanged = Signal()
    headlineChanged = Signal()
    runtimeNoteChanged = Signal()
    taskKeywordChanged = Signal()
    taskStatusFilterChanged = Signal()
    queueKeywordChanged = Signal()
    queueTypeFilterChanged = Signal()
    localKeywordChanged = Signal()
    localStatusFilterChanged = Signal()
    queueFloodWaitTextChanged = Signal()
    taskFilterSummaryChanged = Signal()
    queueFilterSummaryChanged = Signal()
    localFilterSummaryChanged = Signal()

    def __init__(self, *, api_client, local_runtime_service, task_runner: TaskRunner) -> None:
        super().__init__()
        self._api_client = api_client
        self._local_runtime_service = local_runtime_service
        self._task_runner = task_runner

        self._current_tab = "tasks"
        self._summary_cards: list[dict[str, Any]] = []
        self._headline = "任务中心已接入真实数据模型。"
        self._runtime_note = "本地下载、任务队列和服务端记录统一由 Python 状态层驱动。"
        self._task_keyword = ""
        self._task_status_filter = "all"
        self._queue_keyword = ""
        self._queue_type_filter = "all"
        self._local_keyword = ""
        self._local_status_filter = "all"
        self._queue_flood_wait_text = ""
        self._task_filter_summary = ""
        self._queue_filter_summary = ""
        self._local_filter_summary = ""
        self._limit = 100
        self._refresh_scheduled = False

        self._download_groups: list[dict[str, Any]] = []
        self._upload_records: list[dict[str, Any]] = []
        self._queue_snapshot: dict[str, Any] = {}
        self._download_statistics: dict[str, Any] = {}
        self._upload_statistics: dict[str, Any] = {}
        self._local_transfers: dict[str, dict[str, Any]] = {}

        self._active_downloads_model = RoleListModel()
        self._active_uploads_model = RoleListModel()
        self._group_records_model = RoleListModel()
        self._queue_current_model = RoleListModel()
        self._queue_waiting_model = RoleListModel()
        self._local_downloads_model = RoleListModel()

        self._local_runtime_service.transferUpdated.connect(self._handle_transfer_update)
        for item in self._local_runtime_service.list_download_statuses():
            self._local_transfers[item["transferId"]] = item
        self._rebuild_local_downloads()

    def get_summary_cards(self) -> list[dict[str, Any]]:
        return self._summary_cards

    def get_current_tab(self) -> str:
        return self._current_tab

    def get_headline(self) -> str:
        return self._headline

    def get_runtime_note(self) -> str:
        return self._runtime_note

    def get_task_keyword(self) -> str:
        return self._task_keyword

    def get_task_status_filter(self) -> str:
        return self._task_status_filter

    def get_queue_keyword(self) -> str:
        return self._queue_keyword

    def get_queue_type_filter(self) -> str:
        return self._queue_type_filter

    def get_local_keyword(self) -> str:
        return self._local_keyword

    def get_local_status_filter(self) -> str:
        return self._local_status_filter

    def get_queue_flood_wait_text(self) -> str:
        return self._queue_flood_wait_text

    def get_task_filter_summary(self) -> str:
        return self._task_filter_summary

    def get_queue_filter_summary(self) -> str:
        return self._queue_filter_summary

    def get_local_filter_summary(self) -> str:
        return self._local_filter_summary

    def get_active_downloads_model(self) -> QObject:
        return self._active_downloads_model

    def get_active_uploads_model(self) -> QObject:
        return self._active_uploads_model

    def get_group_records_model(self) -> QObject:
        return self._group_records_model

    def get_queue_current_model(self) -> QObject:
        return self._queue_current_model

    def get_queue_waiting_model(self) -> QObject:
        return self._queue_waiting_model

    def get_local_downloads_model(self) -> QObject:
        return self._local_downloads_model

    @Slot(str)
    def setCurrentTab(self, value: str) -> None:
        if value == self._current_tab:
            return
        self._current_tab = value
        self.currentTabChanged.emit()

    @Slot(str)
    def setTaskKeyword(self, value: str) -> None:
        normalized = value.strip()
        if normalized == self._task_keyword:
            return
        self._task_keyword = normalized
        self.taskKeywordChanged.emit()
        self._rebuild_task_models()

    @Slot(str)
    def setTaskStatusFilter(self, value: str) -> None:
        if value == self._task_status_filter:
            return
        self._task_status_filter = value
        self.taskStatusFilterChanged.emit()
        self._rebuild_task_models()

    @Slot(str)
    def setQueueKeyword(self, value: str) -> None:
        normalized = value.strip()
        if normalized == self._queue_keyword:
            return
        self._queue_keyword = normalized
        self.queueKeywordChanged.emit()
        self._rebuild_queue_models()

    @Slot(str)
    def setQueueTypeFilter(self, value: str) -> None:
        if value == self._queue_type_filter:
            return
        self._queue_type_filter = value
        self.queueTypeFilterChanged.emit()
        self._rebuild_queue_models()

    @Slot(str)
    def setLocalKeyword(self, value: str) -> None:
        normalized = value.strip()
        if normalized == self._local_keyword:
            return
        self._local_keyword = normalized
        self.localKeywordChanged.emit()
        self._rebuild_local_downloads()

    @Slot(str)
    def setLocalStatusFilter(self, value: str) -> None:
        if value == self._local_status_filter:
            return
        self._local_status_filter = value
        self.localStatusFilterChanged.emit()
        self._rebuild_local_downloads()

    @Slot()
    def refresh(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._set_error_message("")
        self._task_runner.submit(self._load_snapshot, on_success=self._apply_snapshot, on_error=self._apply_error)

    def _load_snapshot(self) -> dict[str, Any]:
        return {
            "downloads": self._api_client.get_downloads(limit=self._limit, grouped=True),
            "uploads": self._api_client.get_uploads(limit=self._limit),
            "queue": self._api_client.get_queue_status(),
            "download_stats": self._api_client.get_download_statistics(),
            "upload_stats": self._api_client.get_upload_statistics(),
        }

    def _apply_snapshot(self, payload: dict[str, Any]) -> None:
        self._refresh_scheduled = False
        self._set_busy(False)
        downloads_payload = payload.get("downloads") or {}
        uploads_payload = payload.get("uploads") or {}

        self._download_groups = list(downloads_payload.get("data") or [])
        self._upload_records = list(uploads_payload.get("data") or [])
        self._queue_snapshot = payload.get("queue") or {}
        self._download_statistics = (payload.get("download_stats") or {}).get("data") or {}
        self._upload_statistics = (payload.get("upload_stats") or {}).get("data") or {}

        self._headline = "任务中心已完成服务端任务、本地下载和队列快照接线。"
        self._runtime_note = "服务端任务快照和本地下载状态已同步，WebSocket 更新会自动触发局部刷新。"
        self.headlineChanged.emit()
        self.runtimeNoteChanged.emit()
        self._rebuild_models()

    def _apply_error(self, message: str) -> None:
        self._refresh_scheduled = False
        self._set_busy(False)
        self._set_error_message(message)
        self._headline = "任务中心数据拉取失败"
        self.headlineChanged.emit()

    def consume_status_event(self, payload: dict[str, Any]) -> None:
        message_type = str(payload.get("type") or "")
        if message_type not in {
            "initial",
            "download_update",
            "upload_update",
            "cleanup_update",
            "statistics_update",
        }:
            return
        if self._busy or self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        QTimer.singleShot(500, self.refresh)

    def _rebuild_models(self) -> None:
        self._summary_cards = [
            {
                "title": "下载中",
                "value": str(self._download_statistics.get("downloading", 0)),
                "caption": f"总数 {self._download_statistics.get('total', 0)}",
                "tone": "info",
            },
            {
                "title": "上传中",
                "value": str(self._upload_statistics.get("uploading", 0)),
                "caption": f"总数 {self._upload_statistics.get('total', 0)}",
                "tone": "success",
            },
            {
                "title": "记录组",
                "value": str(len(self._download_groups)),
                "caption": f"等待队列 {self._queue_snapshot.get('waiting_count', 0)}",
                "tone": "warning",
            },
            {
                "title": "本地下载",
                "value": str(len(self._local_transfers)),
                "caption": f"活跃 {self._local_active_count()}",
                "tone": "primary",
            },
        ]
        self.summaryCardsChanged.emit()
        self._rebuild_task_models()
        self._rebuild_queue_models()
        self._rebuild_local_downloads()

    def _rebuild_task_models(self) -> None:
        active_downloads = [
            self._normalize_active_download(group, record)
            for group in self._download_groups
            for record in group.get("downloads") or []
            if record.get("status") in {"pending", "waiting", "downloading"}
        ]
        active_uploads = [
            self._normalize_upload_record(record)
            for record in self._upload_records
            if record.get("status") in {"pending", "waiting_download", "uploading"}
        ]
        group_records = [self._normalize_group_record(group) for group in self._download_groups]

        filtered_downloads = [item for item in active_downloads if self._matches_task_item(item)]
        filtered_uploads = [item for item in active_uploads if self._matches_task_item(item)]
        filtered_groups = [item for item in group_records if self._matches_task_item(item)]

        self._active_downloads_model.set_items(filtered_downloads)
        self._active_uploads_model.set_items(filtered_uploads)
        self._group_records_model.set_items(filtered_groups)

        self._task_filter_summary = (
            f"下载 {len(filtered_downloads)}/{len(active_downloads)} · "
            f"上传 {len(filtered_uploads)}/{len(active_uploads)} · "
            f"记录组 {len(filtered_groups)}/{len(group_records)}"
        )
        self.taskFilterSummaryChanged.emit()

    def _rebuild_queue_models(self) -> None:
        current_processing = self._queue_snapshot.get("current_processing")
        current_items = []
        if current_processing and self._matches_queue_item(current_processing):
            current_items.append(self._normalize_queue_item(current_processing, state_label="处理中"))

        waiting_items = [
            self._normalize_queue_item(item, state_label=f"等待 {index + 1}")
            for index, item in enumerate(self._queue_snapshot.get("waiting_items") or [])
            if self._matches_queue_item(item)
        ]
        self._queue_current_model.set_items(current_items)
        self._queue_waiting_model.set_items(waiting_items)

        flood_wait = self._queue_snapshot.get("flood_wait") or {}
        if flood_wait.get("is_waiting"):
            self._queue_flood_wait_text = (
                f"Telegram 限流中，还需等待 {flood_wait.get('remaining_seconds', 0)} 秒。"
            )
        else:
            self._queue_flood_wait_text = ""
        self.queueFloodWaitTextChanged.emit()

        waiting_total = len(self._queue_snapshot.get("waiting_items") or [])
        self._queue_filter_summary = (
            f"处理中 {len(current_items)} · 等待 {len(waiting_items)}/{waiting_total}"
        )
        self.queueFilterSummaryChanged.emit()

    def _rebuild_local_downloads(self) -> None:
        local_items = [
            self._normalize_local_transfer(item)
            for item in self._local_transfers.values()
            if self._matches_local_item(item)
        ]
        local_items.sort(key=self._local_sort_key)
        self._local_downloads_model.set_items(local_items)
        self._local_filter_summary = (
            f"匹配 {len(local_items)} / {len(self._local_transfers)} 项"
        )
        self.localFilterSummaryChanged.emit()

    def _normalize_active_download(self, group: dict[str, Any], record: dict[str, Any]) -> dict[str, Any]:
        progress = format_progress(record.get("completed_length"), record.get("total_length") or record.get("file_size"))
        status = record.get("status") or "pending"
        return {
            "rowType": "download",
            "downloadId": int(record.get("id") or 0),
            "gid": str(record.get("gid") or ""),
            "title": str(record.get("file_name") or "未知文件"),
            "subtitle": str(group.get("caption") or group.get("group_key") or "下载任务"),
            "status": status,
            "statusLabel": self._download_status_label(status, record.get("error_message")),
            "statusTone": self._download_status_tone(status, record.get("error_message")),
            "progressPercent": round(progress, 2),
            "metaPrimary": format_speed(record.get("download_speed")),
            "metaSecondary": format_datetime(record.get("updated_at") or record.get("created_at")),
            "sizeText": self._download_size_text(record),
            "canRetry": bool(record.get("gid") or record.get("source_url")),
            "canDelete": bool(record.get("gid")),
            "error": str(record.get("error_message") or ""),
        }

    def _normalize_upload_record(self, record: dict[str, Any]) -> dict[str, Any]:
        progress = format_progress(record.get("uploaded_size"), record.get("total_size"))
        status = record.get("status") or "pending"
        target = str(record.get("upload_target") or "unknown")
        return {
            "rowType": "upload",
            "uploadId": int(record.get("id") or 0),
            "title": str(record.get("file_name") or "未知文件"),
            "subtitle": f"目标 {target}",
            "status": status,
            "statusLabel": self._upload_status_label(status, target),
            "statusTone": self._upload_status_tone(status),
            "progressPercent": round(progress, 2),
            "metaPrimary": format_speed(record.get("upload_speed")),
            "metaSecondary": format_datetime(record.get("updated_at") or record.get("created_at")),
            "sizeText": format_bytes(record.get("total_size")),
            "canRetry": bool(record.get("id")),
            "canDelete": bool(record.get("id")),
            "error": str(record.get("error_message") or record.get("failure_reason") or ""),
        }

    def _normalize_group_record(self, group: dict[str, Any]) -> dict[str, Any]:
        stats = group.get("stats") or {}
        title = str(group.get("caption") or group.get("group_key") or "记录组")
        status, label, tone = self._group_status(stats, group.get("downloads") or [])
        return {
            "rowType": "group",
            "groupKey": str(group.get("group_key") or title),
            "title": title,
            "subtitle": f"{group.get('group_type', 'group')} · {format_datetime(group.get('created_at'))}",
            "status": status,
            "statusLabel": label,
            "statusTone": tone,
            "progressPercent": round(format_progress(stats.get("completed_size"), stats.get("total_size")), 2),
            "metaPrimary": f"{stats.get('completed', 0)}/{stats.get('total_files', 0)} 完成",
            "metaSecondary": f"下载中 {stats.get('downloading', 0)} · 失败 {stats.get('failed', 0)}",
            "sizeText": format_bytes(stats.get("total_size")),
            "canRetry": False,
            "canDelete": False,
            "error": "",
        }

    def _normalize_queue_item(self, item: dict[str, Any], *, state_label: str) -> dict[str, Any]:
        item_type = str(item.get("type") or "single")
        title = str(item.get("title") or "未命名任务")
        return {
            "queueId": str(item.get("queue_id") or title),
            "title": title,
            "subtitle": f"{'媒体组' if item_type == 'media_group' else '单个文件'} · {state_label}",
            "itemType": item_type,
            "statusLabel": state_label,
            "statusTone": "warning" if state_label.startswith("等待") else "primary",
            "meta": (
                f"文件数 {item.get('media_group_total', 0)}"
                if item_type == "media_group"
                else f"下载任务 {len(item.get('task_gids') or [])}"
            ),
        }

    def _normalize_local_transfer(self, item: dict[str, Any]) -> dict[str, Any]:
        state = str(item.get("state") or "pending")
        total_bytes = item.get("totalBytes")
        return {
            "transferId": str(item.get("transferId") or ""),
            "title": str(item.get("fileName") or "未命名文件"),
            "subtitle": str(item.get("localPath") or ""),
            "status": state,
            "statusLabel": self._local_status_label(state),
            "statusTone": self._local_status_tone(state),
            "progressPercent": float(item.get("progressPercent") or 0),
            "metaPrimary": self._local_meta_text(item),
            "metaSecondary": format_speed(item.get("downloadSpeed")),
            "sizeText": (
                f"{format_bytes(item.get('downloadedBytes'))} / {format_bytes(total_bytes)}"
                if total_bytes
                else format_bytes(item.get("downloadedBytes"))
            ),
            "localPath": str(item.get("localPath") or ""),
            "canCancel": state in {"pending", "downloading"},
            "canRetry": state in {"error", "cancelled"},
            "canOpen": state == "completed",
            "canDelete": state in {"completed", "error", "cancelled"},
            "error": str(item.get("error") or ""),
        }

    def _matches_task_item(self, item: dict[str, Any]) -> bool:
        if self._task_status_filter != "all":
            if self._task_status_filter == "active" and item["status"] not in {"pending", "waiting", "downloading", "waiting_download", "uploading"}:
                return False
            if self._task_status_filter == "failed" and item["status"] not in {"failed", "error"}:
                return False
            if self._task_status_filter == "completed" and item["status"] not in {"completed"}:
                return False

        if not self._task_keyword:
            return True
        query = self._task_keyword.lower()
        return any(query in str(item.get(key, "")).lower() for key in ("title", "subtitle", "statusLabel", "metaPrimary"))

    def _matches_queue_item(self, item: dict[str, Any]) -> bool:
        if self._queue_type_filter != "all" and item.get("type") != self._queue_type_filter:
            return False
        if not self._queue_keyword:
            return True
        query = self._queue_keyword.lower()
        return query in str(item.get("title") or "").lower()

    def _matches_local_item(self, item: dict[str, Any]) -> bool:
        state = str(item.get("state") or "")
        if self._local_status_filter == "active" and state not in {"pending", "downloading", "cancelling"}:
            return False
        if self._local_status_filter == "completed" and state != "completed":
            return False
        if self._local_status_filter == "failed" and state not in {"error", "cancelled"}:
            return False

        if not self._local_keyword:
            return True
        query = self._local_keyword.lower()
        return any(query in str(item.get(key) or "").lower() for key in ("fileName", "localPath", "error"))

    def _download_size_text(self, record: dict[str, Any]) -> str:
        total = record.get("total_length") or record.get("file_size")
        completed = record.get("completed_length")
        if total:
            return f"{format_bytes(completed)} / {format_bytes(total)}"
        return format_bytes(completed)

    def _group_status(self, stats: dict[str, Any], downloads: list[dict[str, Any]]) -> tuple[str, str, str]:
        if stats.get("downloading", 0) > 0:
            return "downloading", "下载中", "warning"

        uploads = [upload for download in downloads for upload in (download.get("uploads") or [])]
        if any(upload.get("status") in {"pending", "waiting_download", "uploading"} for upload in uploads):
            return "uploading", "上传中", "primary"
        if stats.get("failed", 0) > 0 or any(upload.get("status") == "failed" for upload in uploads):
            return "failed", "失败", "danger"
        if stats.get("completed", 0) == stats.get("total_files", 0):
            return "completed", "已完成", "success"
        return "pending", "等待中", "info"

    def _download_status_label(self, status: str, error_message: str | None) -> str:
        if error_message and "跳过" in error_message:
            return "已跳过"
        return {
            "pending": "等待中",
            "waiting": "等待中",
            "downloading": "下载中",
            "completed": "已完成",
            "failed": "失败",
            "skipped": "已跳过",
        }.get(status, status)

    def _download_status_tone(self, status: str, error_message: str | None) -> str:
        if error_message and "跳过" in error_message:
            return "info"
        return {
            "pending": "info",
            "waiting": "info",
            "downloading": "warning",
            "completed": "success",
            "failed": "danger",
            "skipped": "info",
        }.get(status, "info")

    def _upload_status_label(self, status: str, upload_target: str) -> str:
        target = "Telegram" if upload_target == "telegram" else "OneDrive" if upload_target == "onedrive" else upload_target
        mapping = {
            "pending": "等待中",
            "waiting_download": "等待下载",
            "uploading": f"上传到 {target}",
            "completed": "已完成",
            "failed": "失败",
            "cancelled": "已取消",
        }
        return mapping.get(status, status)

    def _upload_status_tone(self, status: str) -> str:
        return {
            "pending": "info",
            "waiting_download": "info",
            "uploading": "primary",
            "completed": "success",
            "failed": "danger",
            "cancelled": "warning",
        }.get(status, "info")

    def _local_status_label(self, state: str) -> str:
        return {
            "pending": "等待中",
            "downloading": "下载中",
            "ready": "可预览",
            "completed": "已完成",
            "error": "失败",
            "cancelling": "取消中",
            "cancelled": "已取消",
        }.get(state, state)

    def _local_status_tone(self, state: str) -> str:
        return {
            "pending": "info",
            "downloading": "warning",
            "ready": "primary",
            "completed": "success",
            "error": "danger",
            "cancelling": "warning",
            "cancelled": "info",
        }.get(state, "info")

    def _local_meta_text(self, item: dict[str, Any]) -> str:
        state = str(item.get("state") or "")
        if state == "completed":
            return "本地文件已就绪"
        if state == "error":
            return str(item.get("error") or "本地下载失败")
        if state == "cancelled":
            return "下载已取消"
        if state == "cancelling":
            return "正在取消下载"
        return "正在写入本地文件"

    def _local_active_count(self) -> int:
        return sum(
            1
            for item in self._local_transfers.values()
            if item.get("state") not in {"completed", "error", "cancelled"}
        )

    def _local_sort_key(self, item: dict[str, Any]) -> tuple[int, str]:
        state = item["status"]
        if state in {"downloading", "pending", "cancelling"}:
            score = 0
        elif state == "completed":
            score = 1
        else:
            score = 2
        return (score, item["title"].lower())

    @Slot(str)
    def retryServerDownload(self, gid: str) -> None:
        if not gid:
            self._set_error_message("下载任务缺少 GID，无法重试")
            return
        self._task_runner.submit(
            lambda: self._api_client.retry_download(gid),
            on_success=lambda result: self._handle_server_action_result(result, "已重新提交下载任务"),
            on_error=self._set_error_message,
        )

    @Slot(str)
    def deleteServerDownload(self, gid: str) -> None:
        if not gid:
            self._set_error_message("下载任务缺少 GID，无法删除")
            return
        self._task_runner.submit(
            lambda: self._api_client.delete_download(gid),
            on_success=lambda result: self._handle_server_action_result(result, "已删除下载任务"),
            on_error=self._set_error_message,
        )

    @Slot(int)
    def retryUpload(self, upload_id: int) -> None:
        if upload_id <= 0:
            self._set_error_message("上传任务 ID 不存在")
            return
        self._task_runner.submit(
            lambda: self._api_client.retry_upload(upload_id),
            on_success=lambda result: self._handle_server_action_result(result, "已重新提交上传任务"),
            on_error=self._set_error_message,
        )

    @Slot(int)
    def deleteUpload(self, upload_id: int) -> None:
        if upload_id <= 0:
            self._set_error_message("上传任务 ID 不存在")
            return
        self._task_runner.submit(
            lambda: self._api_client.delete_upload(upload_id),
            on_success=lambda result: self._handle_server_action_result(result, "已删除上传任务"),
            on_error=self._set_error_message,
        )

    @Slot(str)
    def cancelLocalDownload(self, transfer_id: str) -> None:
        try:
            status = self._local_runtime_service.cancel_download(transfer_id)
        except Exception as exc:
            self._set_error_message(str(exc))
            return
        self._local_transfers[transfer_id] = status
        self._set_info_message(f"正在取消: {status['fileName']}")
        self._rebuild_local_downloads()

    @Slot(str)
    def retryLocalDownload(self, transfer_id: str) -> None:
        try:
            status = self._local_runtime_service.retry_download(transfer_id)
        except Exception as exc:
            self._set_error_message(str(exc))
            return
        self._local_transfers[transfer_id] = status
        self._set_info_message(f"已重新开始下载: {status['fileName']}")
        self._rebuild_local_downloads()

    @Slot(str)
    def removeLocalDownload(self, transfer_id: str) -> None:
        try:
            self._local_runtime_service.remove_download_session(transfer_id)
        except Exception as exc:
            self._set_error_message(str(exc))
            return
        self._local_transfers.pop(transfer_id, None)
        self._set_info_message("已移除本地下载任务")
        self._rebuild_models()

    @Slot(str)
    def openLocalFile(self, local_path: str) -> None:
        try:
            self._local_runtime_service.open_local_file(local_path)
        except Exception as exc:
            self._set_error_message(str(exc))

    @Slot(str)
    def showLocalFileInFolder(self, local_path: str) -> None:
        try:
            self._local_runtime_service.show_local_file_in_folder(local_path)
        except Exception as exc:
            self._set_error_message(str(exc))

    def _handle_server_action_result(self, result: dict[str, Any], fallback_message: str) -> None:
        self._set_info_message(str(result.get("message") or fallback_message))
        self.refresh()

    def _handle_transfer_update(self, payload: dict[str, Any]) -> None:
        transfer_id = str(payload.get("transferId") or "")
        if not transfer_id:
            return
        self._local_transfers[transfer_id] = payload
        self._rebuild_models()

    summaryCards = Property("QVariantList", get_summary_cards, notify=summaryCardsChanged)
    currentTab = Property(str, get_current_tab, notify=currentTabChanged)
    headline = Property(str, get_headline, notify=headlineChanged)
    runtimeNote = Property(str, get_runtime_note, notify=runtimeNoteChanged)
    taskKeyword = Property(str, get_task_keyword, notify=taskKeywordChanged)
    taskStatusFilter = Property(str, get_task_status_filter, notify=taskStatusFilterChanged)
    queueKeyword = Property(str, get_queue_keyword, notify=queueKeywordChanged)
    queueTypeFilter = Property(str, get_queue_type_filter, notify=queueTypeFilterChanged)
    localKeyword = Property(str, get_local_keyword, notify=localKeywordChanged)
    localStatusFilter = Property(str, get_local_status_filter, notify=localStatusFilterChanged)
    queueFloodWaitText = Property(str, get_queue_flood_wait_text, notify=queueFloodWaitTextChanged)
    taskFilterSummary = Property(str, get_task_filter_summary, notify=taskFilterSummaryChanged)
    queueFilterSummary = Property(str, get_queue_filter_summary, notify=queueFilterSummaryChanged)
    localFilterSummary = Property(str, get_local_filter_summary, notify=localFilterSummaryChanged)
    activeDownloadsModel = Property(QObject, get_active_downloads_model, constant=True)
    activeUploadsModel = Property(QObject, get_active_uploads_model, constant=True)
    groupRecordsModel = Property(QObject, get_group_records_model, constant=True)
    queueCurrentModel = Property(QObject, get_queue_current_model, constant=True)
    queueWaitingModel = Property(QObject, get_queue_waiting_model, constant=True)
    localDownloadsModel = Property(QObject, get_local_downloads_model, constant=True)
