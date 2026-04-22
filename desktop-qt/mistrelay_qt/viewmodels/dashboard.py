from __future__ import annotations

from datetime import datetime
from typing import Any

from PySide6.QtCore import Property, QTimer, Signal, Slot

from ..formatters import format_bytes
from ..task_runner import TaskRunner
from .base import BaseViewModel


class DashboardViewModel(BaseViewModel):
    statCardsChanged = Signal()
    resourceCardsChanged = Signal()
    systemInfoChanged = Signal()
    trendSummaryChanged = Signal()
    lastUpdatedChanged = Signal()
    subtitleChanged = Signal()

    def __init__(self, *, api_client, task_runner: TaskRunner) -> None:
        super().__init__()
        self._api_client = api_client
        self._task_runner = task_runner
        self._stat_cards: list[dict[str, Any]] = []
        self._resource_cards: list[dict[str, Any]] = []
        self._system_info: list[dict[str, Any]] = []
        self._trend_summary = "等待监控趋势同步"
        self._last_updated = ""
        self._subtitle = "等待拉取服务端状态"
        self._refresh_scheduled = False

    def get_stat_cards(self) -> list[dict[str, Any]]:
        return self._stat_cards

    def get_resource_cards(self) -> list[dict[str, Any]]:
        return self._resource_cards

    def get_system_info(self) -> list[dict[str, Any]]:
        return self._system_info

    def get_trend_summary(self) -> str:
        return self._trend_summary

    def get_last_updated(self) -> str:
        return self._last_updated

    def get_subtitle(self) -> str:
        return self._subtitle

    @Slot()
    def refresh(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._set_error_message("")
        self._subtitle = "正在同步 Dashboard 数据"
        self.subtitleChanged.emit()
        self._task_runner.submit(self._load_snapshot, on_success=self._apply_snapshot, on_error=self._apply_error)

    def _load_snapshot(self) -> dict[str, Any]:
        status = self._api_client.get_status()
        downloads = self._api_client.get_download_statistics()
        uploads = self._api_client.get_upload_statistics()
        queue = self._api_client.get_queue_status()
        resources = self._api_client.get_system_resources()
        trend = self._api_client.get_system_trend()
        return {
            "status": status,
            "downloads": downloads,
            "uploads": uploads,
            "queue": queue,
            "resources": resources,
            "trend": trend,
        }

    def _apply_snapshot(self, payload: dict[str, Any]) -> None:
        self._refresh_scheduled = False
        self._set_busy(False)
        status = payload.get("status") or {}
        download_stats = (payload.get("downloads") or {}).get("data") or {}
        upload_stats = (payload.get("uploads") or {}).get("data") or {}
        queue_stats = payload.get("queue") or {}
        resources = (payload.get("resources") or {}).get("data") or {}
        trend_points = (payload.get("trend") or {}).get("data") or []

        self._stat_cards = [
            {
                "title": "服务状态",
                "value": str(status.get("server_status") or "running"),
                "caption": f"Bot {status.get('telegram_bot') or '@unknown'}",
                "tone": "primary",
            },
            {
                "title": "下载任务",
                "value": str(download_stats.get("total", 0)),
                "caption": f"进行中 {download_stats.get('downloading', 0)}",
                "tone": "info",
            },
            {
                "title": "上传任务",
                "value": str(upload_stats.get("total", 0)),
                "caption": f"进行中 {upload_stats.get('uploading', 0)}",
                "tone": "success",
            },
            {
                "title": "任务队列",
                "value": str(queue_stats.get("queue_size", 0)),
                "caption": f"等待 {queue_stats.get('waiting_count', 0)}",
                "tone": "warning",
            },
        ]
        self._resource_cards = self._build_resource_cards(resources)
        self._system_info = [
            {"label": "运行时长", "value": str(status.get("uptime") or "-")},
            {"label": "已连接机器人", "value": str(status.get("connected_bots") or 0)},
            {"label": "版本", "value": str(status.get("version") or "-")},
        ]
        self._trend_summary = self._build_trend_summary(trend_points)
        self._last_updated = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
        self._subtitle = "已同步当前服务端快照"
        self.statCardsChanged.emit()
        self.resourceCardsChanged.emit()
        self.systemInfoChanged.emit()
        self.trendSummaryChanged.emit()
        self.lastUpdatedChanged.emit()
        self.subtitleChanged.emit()

    def _apply_error(self, message: str) -> None:
        self._refresh_scheduled = False
        self._set_busy(False)
        self._set_error_message(message)
        self._subtitle = "Dashboard 数据拉取失败"
        self.subtitleChanged.emit()

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
        if self._refresh_scheduled or self._busy:
            return
        self._refresh_scheduled = True
        QTimer.singleShot(800, self.refresh)

    def _build_resource_cards(self, resources: dict[str, Any]) -> list[dict[str, Any]]:
        cpu = resources.get("cpu") or {}
        memory = resources.get("memory") or {}
        disk = resources.get("disk") or {}
        return [
            {
                "title": "CPU",
                "value": f"{float(cpu.get('percent') or 0):.1f}%",
                "caption": "系统实时占用",
                "tone": self._resource_tone(float(cpu.get("percent") or 0)),
                "percent": float(cpu.get("percent") or 0),
            },
            {
                "title": "内存",
                "value": f"{float(memory.get('percent') or 0):.1f}%",
                "caption": f"{format_bytes(memory.get('used'))} / {format_bytes(memory.get('total'))}",
                "tone": self._resource_tone(float(memory.get("percent") or 0)),
                "percent": float(memory.get("percent") or 0),
            },
            {
                "title": "磁盘",
                "value": f"{float(disk.get('percent') or 0):.1f}%",
                "caption": f"{format_bytes(disk.get('used'))} / {format_bytes(disk.get('total'))}",
                "tone": self._resource_tone(float(disk.get("percent") or 0)),
                "percent": float(disk.get("percent") or 0),
            },
        ]

    def _build_trend_summary(self, trend_points: list[dict[str, Any]]) -> str:
        if not trend_points:
            return "监控趋势还没有采样数据"

        recent = trend_points[-1]
        download_speed = format_bytes(recent.get("download")) + "/s"
        upload_speed = format_bytes(recent.get("upload")) + "/s"
        io_usage = format_bytes(recent.get("io")) + "/s"
        return f"最近采样：下载 {download_speed} · 上传 {upload_speed} · IO {io_usage}"

    def _resource_tone(self, percent: float) -> str:
        if percent >= 85:
            return "danger"
        if percent >= 65:
            return "warning"
        return "success"

    statCards = Property("QVariantList", get_stat_cards, notify=statCardsChanged)
    resourceCards = Property("QVariantList", get_resource_cards, notify=resourceCardsChanged)
    systemInfo = Property("QVariantList", get_system_info, notify=systemInfoChanged)
    trendSummary = Property(str, get_trend_summary, notify=trendSummaryChanged)
    lastUpdated = Property(str, get_last_updated, notify=lastUpdatedChanged)
    subtitle = Property(str, get_subtitle, notify=subtitleChanged)
