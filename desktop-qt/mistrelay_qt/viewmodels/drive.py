from __future__ import annotations

from pathlib import Path
from typing import Any

from PySide6.QtCore import Property, QTimer, QUrl, QObject, Signal, Slot

from ..formatters import format_bytes, format_datetime
from ..list_models import RoleListModel
from ..task_runner import TaskRunner
from .base import BaseViewModel

TELEGRAM_GROUP_PATH_PREFIX = "/__tg_group__/"


class DriveViewModel(BaseViewModel):
    subtitleChanged = Signal()
    usageSummaryChanged = Signal()
    currentFilterChanged = Signal()
    searchKeywordChanged = Signal()
    currentPathLabelChanged = Signal()
    canNavigateUpChanged = Signal()
    filterSummaryChanged = Signal()
    selectedItemChanged = Signal()
    previewStateChanged = Signal()
    emptyStateChanged = Signal()

    def __init__(self, *, api_client, local_runtime_service, task_runner: TaskRunner) -> None:
        super().__init__()
        self._api_client = api_client
        self._local_runtime_service = local_runtime_service
        self._task_runner = task_runner

        self._subtitle = "Telegram 网盘浏览与本地预览已切到 PySide 运行时。"
        self._usage_summary = "等待同步 Telegram 媒体容量"
        self._current_filter = "all"
        self._search_keyword = ""
        self._current_path = "/"
        self._filter_summary = ""
        self._empty_state = "当前没有可显示的 Telegram 媒体。"

        self._items_model = RoleListModel()
        self._raw_items: list[dict[str, Any]] = []
        self._visible_items: list[dict[str, Any]] = []
        self._telegram_meta: dict[str, dict[str, Any]] = {}
        self._group_meta: dict[str, dict[str, Any]] = {}
        self._selected_path = ""
        self._selected_item: dict[str, Any] = self._empty_selected_item()
        self._preview_state: dict[str, Any] = self._empty_preview_state()
        self._preview_transfer_id = ""
        self._preview_item_path = ""
        self._preview_token = 0
        self._refresh_scheduled = False

        self._local_runtime_service.transferUpdated.connect(self._handle_transfer_update)

    def get_subtitle(self) -> str:
        return self._subtitle

    def get_usage_summary(self) -> str:
        return self._usage_summary

    def get_current_filter(self) -> str:
        return self._current_filter

    def get_search_keyword(self) -> str:
        return self._search_keyword

    def get_current_path_label(self) -> str:
        if self._current_path == "/":
            return "Telegram 频道"
        group = self._group_meta.get(self._current_path)
        return str(group.get("title") or "媒体组") if group else "Telegram 频道"

    def get_can_navigate_up(self) -> bool:
        return self._current_path != "/"

    def get_filter_summary(self) -> str:
        return self._filter_summary

    def get_selected_item(self) -> dict[str, Any]:
        return dict(self._selected_item)

    def get_preview_state(self) -> dict[str, Any]:
        return dict(self._preview_state)

    def get_empty_state(self) -> str:
        return self._empty_state

    def get_items_model(self) -> QObject:
        return self._items_model

    @Slot()
    def refresh(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._set_error_message("")
        self._task_runner.submit(self._load_snapshot, on_success=self._apply_snapshot, on_error=self._apply_error)

    def _load_snapshot(self) -> dict[str, Any]:
        usage = self._api_client.get_telegram_usage()
        browse = self._api_client.browse_telegram(
            page=1,
            page_size=100,
            search=self._search_keyword,
            media_type=self._filter_media_type(self._current_filter),
            sort_by="message_date",
            sort_desc=True,
        )
        return {"usage": usage, "browse": browse}

    def _apply_snapshot(self, payload: dict[str, Any]) -> None:
        self._refresh_scheduled = False
        self._set_busy(False)
        usage = (payload.get("usage") or {}).get("data") or {}
        browse = payload.get("browse") or {}

        self._usage_summary = (
            f"总数 {usage.get('total_count', 0)} · "
            f"视频 {usage.get('videos', 0)} · "
            f"图片 {usage.get('images', 0)} · "
            f"文档 {usage.get('documents', 0)} · "
            f"容量 {format_bytes(usage.get('total_size'))}"
        )
        self.usageSummaryChanged.emit()

        self._raw_items = self._map_telegram_items(browse.get("items") or [])

        self._subtitle = f"已同步 {len(self._raw_items)} 个 Telegram 项目。"
        self.subtitleChanged.emit()
        self._rebuild_visible_items()

    def _apply_error(self, message: str) -> None:
        self._refresh_scheduled = False
        self._set_busy(False)
        self._set_error_message(message)
        self._subtitle = "Telegram 网盘数据拉取失败"
        self.subtitleChanged.emit()

    def consume_status_event(self, payload: dict[str, Any]) -> None:
        message_type = str(payload.get("type") or "")
        if message_type not in {"initial", "cleanup_update", "statistics_update"}:
            return
        if self._busy or self._refresh_scheduled:
            return
        self._refresh_scheduled = True
        QTimer.singleShot(1000, self.refresh)

    @Slot(str)
    def setCurrentFilter(self, value: str) -> None:
        if value == self._current_filter:
            return
        self._current_filter = value
        self.currentFilterChanged.emit()
        if value != "all" and self._current_path != "/":
            self._current_path = "/"
            self.currentPathLabelChanged.emit()
            self.canNavigateUpChanged.emit()
        self.refresh()

    @Slot(str)
    def setSearchKeyword(self, value: str) -> None:
        normalized = value.strip()
        if normalized == self._search_keyword:
            return
        self._search_keyword = normalized
        self.searchKeywordChanged.emit()

    @Slot()
    def commitSearch(self) -> None:
        self.refresh()

    @Slot()
    def clearSearch(self) -> None:
        if not self._search_keyword:
            return
        self._search_keyword = ""
        self.searchKeywordChanged.emit()
        self.refresh()

    @Slot()
    def navigateUp(self) -> None:
        if self._current_path == "/":
            return
        self._current_path = "/"
        self.currentPathLabelChanged.emit()
        self.canNavigateUpChanged.emit()
        self._rebuild_visible_items()

    @Slot(str)
    def selectItem(self, path: str) -> None:
        if not path or path == self._selected_path:
            return
        self._selected_path = path
        if self._preview_item_path and self._preview_item_path != path:
            self._reset_preview_state(cancel_existing=True)
        self._rebuild_selected_item()

    @Slot(str)
    def activateItem(self, path: str) -> None:
        if not path:
            return
        if path.startswith(TELEGRAM_GROUP_PATH_PREFIX):
            self._selected_path = ""
            self._current_path = path
            self.currentPathLabelChanged.emit()
            self.canNavigateUpChanged.emit()
            self._reset_preview_state(cancel_existing=True)
            self._rebuild_visible_items()
            return

        self.selectItem(path)
        self.openPreview(path)

    @Slot(str)
    def openPreview(self, path: str) -> None:
        target_path = path or self._selected_path
        item = self._find_item_by_path(target_path)
        if not item or item.get("isDir"):
            return

        kind = self._item_kind(item)
        if kind not in {"image", "video"}:
            self._set_info_message("当前文件类型不支持内置预览")
            return

        self._preview_token += 1
        token = self._preview_token
        self._reset_preview_state(cancel_existing=True)
        self._preview_item_path = target_path
        self._preview_state = {
            "mode": kind,
            "source": "",
            "status": "正在准备本地预览缓存",
            "info": item.get("sizeText") or "-",
            "busy": True,
            "ready": False,
        }
        self.previewStateChanged.emit()

        if kind == "image":
            self._task_runner.submit(
                lambda: self._prepare_image_preview(target_path),
                on_success=lambda result: self._apply_image_preview(token, result),
                on_error=lambda message: self._apply_preview_error(token, message),
            )
            return

        self._task_runner.submit(
            lambda: self._start_video_preview(target_path),
            on_success=lambda result: self._apply_video_preview(token, result),
            on_error=lambda message: self._apply_preview_error(token, message),
        )

    @Slot()
    def closePreview(self) -> None:
        self._preview_token += 1
        self._reset_preview_state(cancel_existing=True)

    @Slot(str)
    def downloadItem(self, path: str) -> None:
        target_path = path or self._selected_path
        items = self._resolve_download_items(target_path)
        if not items:
            return

        queued = 0
        existing = 0
        for item in items:
            result = self._local_runtime_service.start_download(
                source_url=self._source_url_for_item(item),
                remote="telegram",
                remote_path=str(item.get("path") or ""),
                file_name=str(item.get("name") or "未命名文件"),
            )
            if result.get("existing"):
                existing += 1
            else:
                queued += 1

        if queued > 0 and existing > 0:
            self._set_info_message(f"已加入下载 {queued} 项，{existing} 项已在队列中")
        elif queued > 0:
            self._set_info_message(f"已加入本地下载 {queued} 项")
        elif existing > 0:
            self._set_info_message("所选文件已在本地下载队列中")

    @Slot(str)
    def deleteItem(self, path: str) -> None:
        target_path = path or self._selected_path
        if not target_path:
            return

        if target_path.startswith(TELEGRAM_GROUP_PATH_PREFIX):
            group = self._group_meta.get(target_path)
            if not group:
                self._set_error_message("媒体组信息缺失，无法删除")
                return
            self._task_runner.submit(
                lambda: self._api_client.delete_telegram_group(str(group.get("mediaGroupId") or "")),
                on_success=lambda result: self._handle_delete_result(result, "已删除媒体组"),
                on_error=self._set_error_message,
            )
            return

        meta = self._telegram_meta.get(target_path)
        message_id = int(meta.get("messageId") or 0) if meta else 0
        if message_id <= 0:
            self._set_error_message("文件消息 ID 缺失，无法删除")
            return
        self._task_runner.submit(
            lambda: self._api_client.delete_telegram_item(message_id),
            on_success=lambda result: self._handle_delete_result(result, "已删除 Telegram 文件"),
            on_error=self._set_error_message,
        )

    @Slot()
    def deleteSelected(self) -> None:
        self.deleteItem(self._selected_path)

    @Slot()
    def clearTelegramMedia(self) -> None:
        self._task_runner.submit(
            self._api_client.clear_telegram_media,
            on_success=lambda result: self._handle_clear_result(result),
            on_error=self._set_error_message,
        )

    def _map_telegram_items(self, records: list[dict[str, Any]]) -> list[dict[str, Any]]:
        items: list[dict[str, Any]] = []
        self._telegram_meta = {}
        self._group_meta = {}

        for record in records:
            message_id = int(record.get("message_id") or 0)
            mime_type = str(record.get("mime_type") or "")
            extension = ""
            if "/" in mime_type:
                extension = f".{mime_type.split('/', 1)[1]}"
            fallback_name = f"media_{message_id}{extension}" if message_id else "media.bin"
            path = f"tg://{message_id}" if message_id else f"tg://{len(items) + 1}"

            self._telegram_meta[path] = {
                "streamUrl": str(record.get("stream_url") or ""),
                "hash": str(record.get("hash") or ""),
                "caption": str(record.get("caption") or ""),
                "duration": record.get("duration"),
                "messageId": message_id,
                "supportsStreaming": bool(record.get("supports_streaming")),
                "mediaGroupId": str(record.get("media_group_id") or ""),
            }

            items.append(
                {
                    "name": str(record.get("file_name") or fallback_name),
                    "path": path,
                    "size": int(record.get("file_size") or 0),
                    "mimeType": mime_type,
                    "modTime": str(record.get("message_date") or ""),
                    "isDir": False,
                }
            )

        return items

    def _rebuild_visible_items(self) -> None:
        self._rebuild_group_meta()
        if self._current_path != "/" and self._current_path not in self._group_meta:
            self._current_path = "/"
            self.currentPathLabelChanged.emit()
            self.canNavigateUpChanged.emit()

        visible_items = self._build_visible_items()
        self._visible_items = visible_items
        self._items_model.set_items(visible_items)

        total = len(self._raw_items)
        visible = len(visible_items)
        self._filter_summary = f"显示 {visible} / {total} 项"
        self.filterSummaryChanged.emit()

        self._empty_state = (
            "当前筛选下没有匹配的 Telegram 媒体。"
            if total > 0
            else "Telegram 频道还没有可浏览的媒体文件。"
        )
        self.emptyStateChanged.emit()

        if not any(item.get("path") == self._selected_path for item in visible_items):
            self._selected_path = visible_items[0]["path"] if visible_items else ""
            if self._preview_item_path and self._preview_item_path != self._selected_path:
                self._reset_preview_state(cancel_existing=True)
        self._rebuild_selected_item()

    def _build_visible_items(self) -> list[dict[str, Any]]:
        if self._current_path != "/":
            group_items = self._group_members(self._current_path)
            rows = [self._normalize_file_item(item) for item in group_items]
            rows.sort(key=self._item_sort_key, reverse=True)
            return rows

        if self._current_filter != "all":
            items = [self._normalize_file_item(item) for item in self._raw_items]
            items.sort(key=self._item_sort_key, reverse=True)
            return items

        group_rows: list[dict[str, Any]] = []
        for group_path, group in self._group_meta.items():
            group_rows.append(
                {
                    "path": group_path,
                    "title": str(group.get("title") or "媒体组"),
                    "kind": "group",
                    "subtitle": f"{group.get('count', 0)} 个文件",
                    "metaPrimary": format_bytes(group.get("size")),
                    "metaSecondary": format_datetime(group.get("modTime")),
                    "sizeText": format_bytes(group.get("size")),
                    "timeText": format_datetime(group.get("modTime")),
                    "sortTime": str(group.get("modTime") or ""),
                    "tone": "warning",
                    "isDir": True,
                    "canPreview": False,
                    "canDownload": True,
                    "canDelete": True,
                }
            )

        singles = [
            item
            for item in self._raw_items
            if not str((self._telegram_meta.get(str(item.get("path") or "")) or {}).get("mediaGroupId") or "")
        ]
        single_rows = [self._normalize_file_item(item) for item in singles]
        group_rows.sort(key=self._group_sort_key, reverse=True)
        single_rows.sort(key=self._item_sort_key, reverse=True)
        return [*group_rows, *single_rows]

    def _rebuild_group_meta(self) -> None:
        grouped: dict[str, list[dict[str, Any]]] = {}
        for item in self._raw_items:
            media_group_id = str((self._telegram_meta.get(str(item.get("path") or "")) or {}).get("mediaGroupId") or "")
            if media_group_id:
                grouped.setdefault(media_group_id, []).append(item)

        next_group_meta: dict[str, dict[str, Any]] = {}
        for media_group_id, members in grouped.items():
            members.sort(key=lambda item: str(item.get("modTime") or ""), reverse=True)
            group_path = f"{TELEGRAM_GROUP_PATH_PREFIX}{media_group_id}"
            next_group_meta[group_path] = {
                "mediaGroupId": media_group_id,
                "title": self._build_group_title(media_group_id, members),
                "count": len(members),
                "size": sum(int(member.get("size") or 0) for member in members),
                "modTime": str(members[0].get("modTime") or ""),
                "memberPaths": [str(member.get("path") or "") for member in members],
            }
        self._group_meta = next_group_meta

    def _rebuild_selected_item(self) -> None:
        if not self._selected_path:
            self._selected_item = self._empty_selected_item()
            self.selectedItemChanged.emit()
            return

        group = self._group_meta.get(self._selected_path)
        if group is not None:
            self._selected_item = {
                "path": self._selected_path,
                "title": str(group.get("title") or "媒体组"),
                "subtitle": f"{group.get('count', 0)} 个文件",
                "metaPrimary": format_bytes(group.get("size")),
                "metaSecondary": format_datetime(group.get("modTime")),
                "kindLabel": "媒体组",
                "canPreview": False,
                "canDownload": True,
                "canDelete": True,
                "isDir": True,
                "hasSelection": True,
            }
            self.selectedItemChanged.emit()
            return

        item = self._find_item_by_path(self._selected_path)
        if not item:
            self._selected_item = self._empty_selected_item()
            self.selectedItemChanged.emit()
            return

        kind = self._item_kind(item)
        self._selected_item = {
            "path": str(item.get("path") or ""),
            "title": str(item.get("name") or "未命名文件"),
            "subtitle": str((self._telegram_meta.get(str(item.get("path") or "")) or {}).get("caption") or self._kind_label(kind)),
            "metaPrimary": format_bytes(item.get("size")),
            "metaSecondary": format_datetime(item.get("modTime")),
            "kindLabel": self._kind_label(kind),
            "canPreview": kind in {"image", "video"},
            "canDownload": True,
            "canDelete": True,
            "isDir": False,
            "hasSelection": True,
        }
        self.selectedItemChanged.emit()

    def _empty_selected_item(self) -> dict[str, Any]:
        return {
            "path": "",
            "title": "",
            "subtitle": "选择一个文件或媒体组以查看详情",
            "metaPrimary": "-",
            "metaSecondary": "-",
            "kindLabel": "",
            "canPreview": False,
            "canDownload": False,
            "canDelete": False,
            "isDir": False,
            "hasSelection": False,
        }

    def _empty_preview_state(self) -> dict[str, Any]:
        return {
            "mode": "none",
            "source": "",
            "status": "选择图片或视频后可在右侧预览",
            "info": "",
            "busy": False,
            "ready": False,
        }

    def _reset_preview_state(self, *, cancel_existing: bool) -> None:
        if cancel_existing and self._preview_transfer_id:
            try:
                self._local_runtime_service.cancel_preview(self._preview_transfer_id)
            except Exception:
                pass
        self._preview_transfer_id = ""
        self._preview_item_path = ""
        self._preview_state = self._empty_preview_state()
        self.previewStateChanged.emit()

    def _prepare_image_preview(self, path: str) -> dict[str, Any]:
        item = self._find_item_by_path(path)
        if not item:
            raise RuntimeError("未找到需要预览的图片")
        result = self._local_runtime_service.prepare_preview_file(
            source_url=self._source_url_for_item(item),
            remote="telegram",
            remote_path=str(item.get("path") or ""),
            file_name=str(item.get("name") or "image"),
        )
        local_path = str(result.get("localPath") or "")
        return {
            "source": QUrl.fromLocalFile(local_path).toString(),
            "info": local_path,
        }

    def _apply_image_preview(self, token: int, payload: dict[str, Any]) -> None:
        if token != self._preview_token:
            return
        self._preview_state = {
            "mode": "image",
            "source": str(payload.get("source") or ""),
            "status": "图片预览已就绪",
            "info": str(payload.get("info") or ""),
            "busy": False,
            "ready": True,
        }
        self.previewStateChanged.emit()

    def _start_video_preview(self, path: str) -> dict[str, Any]:
        item = self._find_item_by_path(path)
        if not item:
            raise RuntimeError("未找到需要预览的视频")
        return self._local_runtime_service.start_preview_stream(
            source_url=self._source_url_for_item(item),
            remote="telegram",
            remote_path=str(item.get("path") or ""),
            file_name=str(item.get("name") or "video"),
        )

    def _apply_video_preview(self, token: int, payload: dict[str, Any]) -> None:
        if token != self._preview_token:
            transfer_id = str(payload.get("transferId") or "")
            if transfer_id:
                try:
                    self._local_runtime_service.cancel_preview(transfer_id)
                except Exception:
                    pass
            return

        self._preview_transfer_id = str(payload.get("transferId") or "")
        ready = bool(payload.get("readyForPreview"))
        self._preview_state = {
            "mode": "video",
            "source": str(payload.get("streamUrl") or ""),
            "status": "视频已达到可播放阈值" if ready else "正在准备本地播放缓存",
            "info": "本地流已可播放" if ready else "达到缓存阈值后即可开始播放",
            "busy": not ready,
            "ready": ready,
        }
        self.previewStateChanged.emit()

    def _apply_preview_error(self, token: int, message: str) -> None:
        if token != self._preview_token:
            return
        self._preview_transfer_id = ""
        self._preview_state = {
            "mode": self._preview_state.get("mode") or "none",
            "source": "",
            "status": "预览准备失败",
            "info": message,
            "busy": False,
            "ready": False,
        }
        self.previewStateChanged.emit()
        self._set_error_message(message)

    def _handle_transfer_update(self, payload: dict[str, Any]) -> None:
        if str(payload.get("transferId") or "") != self._preview_transfer_id:
            return

        state = str(payload.get("state") or "")
        if state == "error":
            self._preview_state["status"] = "本地播放缓存失败"
            self._preview_state["info"] = str(payload.get("error") or "未知错误")
            self._preview_state["busy"] = False
            self._preview_state["ready"] = False
        elif state == "completed":
            self._preview_state["status"] = "视频缓存完成"
            self._preview_state["info"] = self._preview_info(payload)
            self._preview_state["busy"] = False
            self._preview_state["ready"] = True
        elif state == "ready":
            self._preview_state["status"] = "视频已达到可播放阈值"
            self._preview_state["info"] = self._preview_info(payload)
            self._preview_state["busy"] = False
            self._preview_state["ready"] = True
        else:
            self._preview_state["status"] = "正在准备本地播放缓存"
            self._preview_state["info"] = self._preview_info(payload)
            self._preview_state["busy"] = True
            self._preview_state["ready"] = False
        self.previewStateChanged.emit()

    def _preview_info(self, payload: dict[str, Any]) -> str:
        downloaded = format_bytes(payload.get("downloadedBytes"))
        total = payload.get("totalBytes")
        speed = int(payload.get("downloadSpeed") or 0)
        total_text = format_bytes(total) if total else "未知"
        if speed > 0:
            return f"已缓存 {downloaded} / {total_text} · {format_bytes(speed)}/s"
        return f"已缓存 {downloaded} / {total_text}"

    def _handle_delete_result(self, result: dict[str, Any], fallback_message: str) -> None:
        self._set_info_message(str(result.get("message") or fallback_message))
        self._selected_path = ""
        self._reset_preview_state(cancel_existing=True)
        if self._current_path != "/" and self._current_path not in self._group_meta:
            self._current_path = "/"
            self.currentPathLabelChanged.emit()
            self.canNavigateUpChanged.emit()
        self.refresh()

    def _handle_clear_result(self, result: dict[str, Any]) -> None:
        self._set_info_message(str(result.get("message") or "已清空 Telegram 媒体"))
        self._selected_path = ""
        self._current_path = "/"
        self.currentPathLabelChanged.emit()
        self.canNavigateUpChanged.emit()
        self._reset_preview_state(cancel_existing=True)
        self.refresh()

    def _resolve_download_items(self, path: str) -> list[dict[str, Any]]:
        if not path:
            return []
        if path.startswith(TELEGRAM_GROUP_PATH_PREFIX):
            return self._group_members(path)
        item = self._find_item_by_path(path)
        return [item] if item else []

    def _group_members(self, group_path: str) -> list[dict[str, Any]]:
        group = self._group_meta.get(group_path) or {}
        member_paths = list(group.get("memberPaths") or [])
        items = [self._find_item_by_path(path) for path in member_paths]
        return [item for item in items if item is not None]

    def _find_item_by_path(self, path: str) -> dict[str, Any] | None:
        for item in self._raw_items:
            if item.get("path") == path:
                return item
        return None

    def _normalize_file_item(self, item: dict[str, Any]) -> dict[str, Any]:
        kind = self._item_kind(item)
        meta = self._telegram_meta.get(str(item.get("path") or "")) or {}
        return {
            "path": str(item.get("path") or ""),
            "title": str(item.get("name") or "未命名文件"),
            "kind": kind,
            "subtitle": str(meta.get("caption") or self._kind_label(kind)),
            "metaPrimary": format_bytes(item.get("size")),
            "metaSecondary": format_datetime(item.get("modTime")),
            "sizeText": format_bytes(item.get("size")),
            "timeText": format_datetime(item.get("modTime")),
            "sortTime": str(item.get("modTime") or ""),
            "tone": self._kind_tone(kind),
            "isDir": False,
            "canPreview": kind in {"image", "video"},
            "canDownload": True,
            "canDelete": True,
        }

    def _item_sort_key(self, item: dict[str, Any]) -> tuple[int, str]:
        return (0, str(item.get("sortTime") or item.get("modTime") or ""))

    def _group_sort_key(self, item: dict[str, Any]) -> tuple[int, str]:
        return (0, str(item.get("sortTime") or ""))

    def _build_group_title(self, media_group_id: str, members: list[dict[str, Any]]) -> str:
        for member in members:
            meta = self._telegram_meta.get(str(member.get("path") or "")) or {}
            caption = str(meta.get("caption") or "").strip()
            if caption:
                return caption[:48]
        suffix = media_group_id[-8:] if len(media_group_id) >= 8 else media_group_id
        return f"媒体组 {suffix}"

    def _source_url_for_item(self, item: dict[str, Any]) -> str:
        path = str(item.get("path") or "")
        meta = self._telegram_meta.get(path) or {}
        raw_stream_url = str(meta.get("streamUrl") or "").strip()
        fallback_short_path = ""
        if meta.get("hash") and meta.get("messageId"):
            fallback_short_path = f"/{meta['hash']}{meta['messageId']}"

        if not raw_stream_url and not fallback_short_path:
            raise RuntimeError("Telegram 直链地址缺失，请刷新后重试")
        if raw_stream_url.startswith("http://") or raw_stream_url.startswith("https://"):
            return raw_stream_url

        normalized_path = fallback_short_path
        if raw_stream_url:
            normalized_path = f"/{raw_stream_url.lstrip('/')}"
        return self._api_client.resolve_server_url(normalized_path)

    def _filter_media_type(self, value: str) -> str:
        return {
            "videos": "video",
            "images": "image",
            "documents": "document",
        }.get(value, "")

    def _item_kind(self, item: dict[str, Any]) -> str:
        if item.get("isDir"):
            return "group"
        mime_type = str(item.get("mimeType") or "")
        suffix = Path(str(item.get("name") or "")).suffix.lower()
        if mime_type.startswith("image/") or suffix in {".jpg", ".jpeg", ".png", ".gif", ".webp", ".bmp"}:
            return "image"
        if mime_type.startswith("video/") or suffix in {".mp4", ".mkv", ".mov", ".webm", ".m4v"}:
            return "video"
        return "document"

    def _kind_label(self, kind: str) -> str:
        return {
            "group": "媒体组",
            "image": "图片",
            "video": "视频",
            "document": "文档",
        }.get(kind, "文件")

    def _kind_tone(self, kind: str) -> str:
        return {
            "group": "warning",
            "image": "success",
            "video": "primary",
            "document": "info",
        }.get(kind, "info")

    subtitle = Property(str, get_subtitle, notify=subtitleChanged)
    usageSummary = Property(str, get_usage_summary, notify=usageSummaryChanged)
    currentFilter = Property(str, get_current_filter, notify=currentFilterChanged)
    searchKeyword = Property(str, get_search_keyword, notify=searchKeywordChanged)
    currentPathLabel = Property(str, get_current_path_label, notify=currentPathLabelChanged)
    canNavigateUp = Property(bool, get_can_navigate_up, notify=canNavigateUpChanged)
    filterSummary = Property(str, get_filter_summary, notify=filterSummaryChanged)
    selectedItem = Property("QVariantMap", get_selected_item, notify=selectedItemChanged)
    previewState = Property("QVariantMap", get_preview_state, notify=previewStateChanged)
    emptyState = Property(str, get_empty_state, notify=emptyStateChanged)
    itemsModel = Property(QObject, get_items_model, constant=True)
