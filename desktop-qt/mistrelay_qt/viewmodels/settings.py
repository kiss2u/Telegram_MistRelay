from __future__ import annotations

from typing import Any

from PySide6.QtCore import QObject, Property, QCoreApplication, QTimer, Signal, Slot

from ..formatters import format_bytes
from ..list_models import RoleListModel
from ..models import DownloadedUpdate, UpdateInfo
from ..paths import logs_root
from ..task_runner import TaskRunner
from .base import BaseViewModel

SERVER_CATEGORY_DEFS: dict[str, dict[str, Any]] = {
    "telegram": {
        "label": "Telegram",
        "fields": [
            {"key": "API_ID", "label": "API ID", "type": "int"},
            {"key": "API_HASH", "label": "API Hash", "type": "password"},
            {"key": "BOT_TOKEN", "label": "Bot Token", "type": "password"},
            {"key": "ADMIN_ID", "label": "管理员 ID", "type": "int"},
            {"key": "FORWARD_ID", "label": "转发 ID", "type": "string"},
            {"key": "UP_TELEGRAM", "label": "上传到 Telegram", "type": "bool"},
        ],
    },
    "rclone": {
        "label": "Rclone",
        "fields": [
            {"key": "UP_ONEDRIVE", "label": "启用 OneDrive 上传", "type": "bool"},
            {"key": "RCLONE_REMOTE", "label": "OneDrive Remote", "type": "string"},
            {"key": "RCLONE_PATH", "label": "OneDrive 路径", "type": "string"},
            {"key": "UP_GOOGLE_DRIVE", "label": "启用 Google Drive 上传", "type": "bool"},
            {"key": "GOOGLE_DRIVE_REMOTE", "label": "Google Drive Remote", "type": "string"},
            {"key": "GOOGLE_DRIVE_PATH", "label": "Google Drive 路径", "type": "string"},
            {"key": "AUTO_DELETE_AFTER_UPLOAD", "label": "上传后自动删除", "type": "bool"},
        ],
    },
    "download": {
        "label": "下载",
        "fields": [
            {"key": "SAVE_PATH", "label": "保存路径", "type": "string"},
            {"key": "PROXY_IP", "label": "服务端代理 IP", "type": "string"},
            {"key": "PROXY_PORT", "label": "服务端代理端口", "type": "string"},
            {"key": "SKIP_SMALL_FILES", "label": "跳过小文件", "type": "bool"},
            {"key": "MIN_FILE_SIZE_MB", "label": "最小文件大小 (MB)", "type": "int"},
        ],
    },
    "aria2": {
        "label": "Aria2",
        "fields": [
            {"key": "RPC_SECRET", "label": "RPC Secret", "type": "password"},
            {"key": "RPC_URL", "label": "RPC URL", "type": "string"},
        ],
    },
    "stream": {
        "label": "直链",
        "fields": [
            {"key": "ENABLE_STREAM", "label": "启用直链", "type": "bool"},
            {"key": "BIN_CHANNEL", "label": "日志频道", "type": "string"},
            {"key": "STREAM_PORT", "label": "端口", "type": "int"},
            {"key": "STREAM_BIND_ADDRESS", "label": "绑定地址", "type": "string"},
            {"key": "STREAM_HASH_LENGTH", "label": "哈希长度", "type": "int"},
            {"key": "STREAM_HAS_SSL", "label": "启用 SSL", "type": "bool"},
            {"key": "STREAM_NO_PORT", "label": "隐藏端口", "type": "bool"},
            {"key": "STREAM_FQDN", "label": "FQDN", "type": "string"},
            {"key": "STREAM_KEEP_ALIVE", "label": "保持活跃", "type": "bool"},
            {"key": "STREAM_PING_INTERVAL", "label": "Ping 间隔", "type": "int"},
            {"key": "STREAM_USE_SESSION_FILE", "label": "使用会话文件", "type": "bool"},
            {"key": "STREAM_ALLOWED_USERS", "label": "允许用户", "type": "string"},
            {"key": "STREAM_AUTO_DOWNLOAD", "label": "自动下载", "type": "bool"},
            {"key": "SEND_STREAM_LINK", "label": "发送直链", "type": "bool"},
            {"key": "MULTI_BOT_TOKENS", "label": "多 Bot Tokens", "type": "multiline"},
        ],
    },
}


class SettingsViewModel(BaseViewModel):
    updateProgressReported = Signal(int, int, bool)

    serverBaseUrlChanged = Signal()
    proxyEnabledChanged = Signal()
    proxyUrlChanged = Signal()
    downloadDirChanged = Signal()
    maxConcurrentDownloadsChanged = Signal()
    threadsPerDownloadChanged = Signal()

    updateStateChanged = Signal()
    updateNotesChanged = Signal()
    manualUrlChanged = Signal()
    updateVersionChanged = Signal()
    updateAvailableChanged = Signal()
    canInstallUpdateChanged = Signal()
    updateProgressPercentChanged = Signal()

    serverCategoriesChanged = Signal()
    serverStatusMessageChanged = Signal()
    rcloneConfigTextChanged = Signal()
    rcloneConfigPathChanged = Signal()
    rcloneRemotesChanged = Signal()

    dockerStatusChanged = Signal()
    dockerLogsChanged = Signal()
    dockerLogLinesChanged = Signal()
    resourceCardsChanged = Signal()
    appLogTextChanged = Signal()
    appLogSummaryChanged = Signal()
    selectedLogFileChanged = Signal()
    logLevelChanged = Signal()
    logKeywordChanged = Signal()
    logTailCountChanged = Signal()

    def __init__(
        self,
        *,
        api_client,
        config_service,
        local_runtime_service,
        update_service,
        task_runner: TaskRunner,
    ) -> None:
        super().__init__()
        self._api_client = api_client
        self._config_service = config_service
        self._local_runtime_service = local_runtime_service
        self._update_service = update_service
        self._task_runner = task_runner

        config = self._config_service.config
        self._server_base_url = config.server_base_url
        self._proxy_enabled = config.proxy.enabled
        self._proxy_url = config.proxy.url
        self._download_dir = (
            config.download.download_dir
            or self._local_runtime_service.get_default_download_dir()
        )
        self._max_concurrent_downloads = config.download.max_concurrent_downloads
        self._threads_per_download = config.download.threads_per_download

        self._update_state = "尚未检查更新"
        self._update_notes = ""
        self._manual_url = ""
        self._update_version = ""
        self._update_available = False
        self._can_install_update = False
        self._update_progress_percent = -1
        self._pending_update: UpdateInfo | None = None

        self._server_categories = [
            {"key": key, "label": value["label"]}
            for key, value in SERVER_CATEGORY_DEFS.items()
        ]
        self._server_values: dict[str, dict[str, Any]] = {}
        self._server_status_message = "等待读取服务端配置"
        self._server_fields_model = RoleListModel()

        self._rclone_config_text = ""
        self._rclone_config_path = "/root/.config/rclone/rclone.conf"
        self._rclone_remotes: list[dict[str, Any]] = []

        self._docker_status: dict[str, Any] = {}
        self._docker_logs = ""
        self._docker_log_lines = 100
        self._resource_cards: list[dict[str, Any]] = []

        self._log_files_model = RoleListModel()
        self._app_log_text = ""
        self._app_log_summary = "暂无日志数据"
        self._selected_log_file = ""
        self._log_level = ""
        self._log_keyword = ""
        self._log_tail_count = 200

        self._bootstrapped = False
        self._resource_refresh_scheduled = False

        self.updateProgressReported.connect(self._apply_update_progress)

    @Slot()
    def bootstrap(self) -> None:
        if not self._bootstrapped:
            self._bootstrapped = True
            self.loadServerCategory("telegram")
            self.loadRcloneConfigFile()
            self.loadAppLogFiles()
        self.loadManagementSnapshot()

    def shutdown(self) -> None:
        self._resource_refresh_scheduled = False

    def consume_status_event(self, payload: dict[str, Any]) -> None:
        message_type = str(payload.get("type") or "")
        if message_type not in {"initial", "statistics_update"}:
            return
        if self._resource_refresh_scheduled:
            return
        self._resource_refresh_scheduled = True
        QTimer.singleShot(1200, self.loadSystemResources)

    def get_server_base_url(self) -> str:
        return self._server_base_url

    def get_proxy_enabled(self) -> bool:
        return self._proxy_enabled

    def get_proxy_url(self) -> str:
        return self._proxy_url

    def get_download_dir(self) -> str:
        return self._download_dir

    def get_max_concurrent_downloads(self) -> int:
        return self._max_concurrent_downloads

    def get_threads_per_download(self) -> int:
        return self._threads_per_download

    def get_update_state(self) -> str:
        return self._update_state

    def get_update_notes(self) -> str:
        return self._update_notes

    def get_manual_url(self) -> str:
        return self._manual_url

    def get_update_version(self) -> str:
        return self._update_version

    def get_update_available(self) -> bool:
        return self._update_available

    def get_can_install_update(self) -> bool:
        return self._can_install_update

    def get_update_progress_percent(self) -> int:
        return self._update_progress_percent

    def get_server_categories(self) -> list[dict[str, str]]:
        return list(self._server_categories)

    def get_server_status_message(self) -> str:
        return self._server_status_message

    def get_server_fields_model(self) -> QObject:
        return self._server_fields_model

    def get_rclone_config_text(self) -> str:
        return self._rclone_config_text

    def get_rclone_config_path(self) -> str:
        return self._rclone_config_path

    def get_rclone_remotes(self) -> list[dict[str, Any]]:
        return list(self._rclone_remotes)

    def get_docker_status(self) -> dict[str, Any]:
        return dict(self._docker_status)

    def get_docker_logs(self) -> str:
        return self._docker_logs

    def get_docker_log_lines(self) -> int:
        return self._docker_log_lines

    def get_resource_cards(self) -> list[dict[str, Any]]:
        return list(self._resource_cards)

    def get_log_files_model(self) -> QObject:
        return self._log_files_model

    def get_app_log_text(self) -> str:
        return self._app_log_text

    def get_app_log_summary(self) -> str:
        return self._app_log_summary

    def get_selected_log_file(self) -> str:
        return self._selected_log_file

    def get_log_level(self) -> str:
        return self._log_level

    def get_log_keyword(self) -> str:
        return self._log_keyword

    def get_log_tail_count(self) -> int:
        return self._log_tail_count

    @Slot(str)
    def setServerBaseUrl(self, value: str) -> None:
        normalized = value.strip().rstrip("/")
        if normalized == self._server_base_url:
            return
        self._server_base_url = normalized
        self.serverBaseUrlChanged.emit()

    @Slot(bool)
    def setProxyEnabled(self, value: bool) -> None:
        if value == self._proxy_enabled:
            return
        self._proxy_enabled = value
        self.proxyEnabledChanged.emit()

    @Slot(str)
    def setProxyUrl(self, value: str) -> None:
        normalized = value.strip()
        if normalized == self._proxy_url:
            return
        self._proxy_url = normalized
        self.proxyUrlChanged.emit()

    @Slot(str)
    def setDownloadDir(self, value: str) -> None:
        normalized = value.strip()
        if normalized == self._download_dir:
            return
        self._download_dir = normalized
        self.downloadDirChanged.emit()

    @Slot(int)
    def setMaxConcurrentDownloads(self, value: int) -> None:
        normalized = max(1, int(value))
        if normalized == self._max_concurrent_downloads:
            return
        self._max_concurrent_downloads = normalized
        self.maxConcurrentDownloadsChanged.emit()

    @Slot(int)
    def setThreadsPerDownload(self, value: int) -> None:
        normalized = max(1, int(value))
        if normalized == self._threads_per_download:
            return
        self._threads_per_download = normalized
        self.threadsPerDownloadChanged.emit()

    @Slot()
    def save(self) -> None:
        self._config_service.update_runtime_settings(
            server_base_url=self._server_base_url,
            proxy_enabled=self._proxy_enabled,
            proxy_url=self._proxy_url,
            download_dir=self._download_dir,
            max_concurrent_downloads=self._max_concurrent_downloads,
            threads_per_download=self._threads_per_download,
        )
        self._set_info_message("客户端配置已保存")

    @Slot()
    def pickDownloadDir(self) -> None:
        selected = self._local_runtime_service.pick_download_dir(self._download_dir)
        if selected and selected != self._download_dir:
            self._download_dir = selected
            self.downloadDirChanged.emit()

    @Slot()
    def checkForUpdates(self) -> None:
        if self._busy:
            return
        self._set_busy(True)
        self._update_progress_percent = -1
        self.updateProgressPercentChanged.emit()
        self._update_state = "正在检查更新"
        self.updateStateChanged.emit()
        self._task_runner.submit(
            self._update_service.check_for_updates,
            on_success=self._apply_update_result,
            on_error=self._apply_update_error,
        )

    @Slot()
    def installUpdate(self) -> None:
        if self._busy:
            return
        if not self._pending_update or not self._pending_update.installable:
            self._set_error_message("当前没有可自动安装的更新")
            return
        self._set_busy(True)
        self._update_progress_percent = 0
        self.updateProgressPercentChanged.emit()
        self._update_state = f"正在下载 v{self._pending_update.version}"
        self.updateStateChanged.emit()
        self._task_runner.submit(
            self._download_and_install_update,
            on_success=self._apply_install_result,
            on_error=self._apply_update_error,
        )

    def _download_and_install_update(self) -> DownloadedUpdate:
        assert self._pending_update is not None
        downloaded = self._update_service.download_update(
            self._pending_update,
            on_progress=lambda downloaded_bytes, total_bytes, done: self.updateProgressReported.emit(
                int(downloaded_bytes),
                int(total_bytes or 0),
                bool(done),
            ),
        )
        self._update_service.install_update(downloaded)
        return downloaded

    def _apply_update_result(self, info: UpdateInfo) -> None:
        self._set_busy(False)
        self._pending_update = info if info.available else None
        self._update_version = info.version
        self._update_available = info.available
        self._can_install_update = bool(info.installable)
        self._update_state = info.message or ("发现新版本" if info.available else "当前已是最新版本")
        notes = info.notes
        if info.download_url:
            notes = "\n".join(filter(None, [notes, f"下载地址：{info.download_url}"]))
        self._update_notes = notes
        self._manual_url = info.manual_url
        self.updateVersionChanged.emit()
        self.updateAvailableChanged.emit()
        self.canInstallUpdateChanged.emit()
        self.updateStateChanged.emit()
        self.updateNotesChanged.emit()
        self.manualUrlChanged.emit()

    def _apply_update_error(self, message: str) -> None:
        self._set_busy(False)
        self._update_state = f"更新失败：{message}"
        self.updateStateChanged.emit()

    def _apply_install_result(self, downloaded: DownloadedUpdate) -> None:
        self._set_busy(False)
        self._update_state = f"已下载 {downloaded.version}，正在静默安装并重启"
        self.updateStateChanged.emit()
        self._set_info_message("更新安装器已启动，客户端即将重启")
        QTimer.singleShot(250, QCoreApplication.quit)

    def _apply_update_progress(self, downloaded: int, total: int, done: bool) -> None:
        if total > 0:
            self._update_progress_percent = max(0, min(100, round((downloaded / total) * 100)))
        elif done:
            self._update_progress_percent = 100
        else:
            self._update_progress_percent = 0
        self.updateProgressPercentChanged.emit()
        if done:
            self._update_state = "下载完成，正在准备安装"
        else:
            self._update_state = f"正在下载更新… {format_bytes(downloaded)} / {format_bytes(total)}"
        self.updateStateChanged.emit()

    @Slot()
    def openManualUpdateUrl(self) -> None:
        if self._manual_url:
            self._local_runtime_service.open_external_url(self._manual_url)

    @Slot(str)
    def loadServerCategory(self, category: str) -> None:
        if category not in SERVER_CATEGORY_DEFS:
            self._set_error_message(f"未知配置分类：{category}")
            return
        self._server_status_message = f"正在读取 {SERVER_CATEGORY_DEFS[category]['label']} 配置"
        self.serverStatusMessageChanged.emit()
        self._task_runner.submit(
            lambda: self._api_client.get_config(category),
            on_success=lambda payload: self._apply_server_category(category, payload),
            on_error=self._apply_server_error,
        )

    def _apply_server_category(self, category: str, payload: dict[str, Any]) -> None:
        self._server_values[category] = dict((payload.get("data") or {}))
        self._server_status_message = f"{SERVER_CATEGORY_DEFS[category]['label']} 配置已同步"
        self.serverStatusMessageChanged.emit()
        self._rebuild_server_fields(category)

    def _apply_server_error(self, message: str) -> None:
        self._server_status_message = f"服务端配置读取失败：{message}"
        self.serverStatusMessageChanged.emit()
        self._set_error_message(message)

    def _rebuild_server_fields(self, category: str) -> None:
        current = self._server_values.get(category) or {}
        items: list[dict[str, Any]] = []
        for field in SERVER_CATEGORY_DEFS[category]["fields"]:
            raw_value = current.get(field["key"])
            if field["type"] == "multiline":
                value = "\n".join(raw_value) if isinstance(raw_value, list) else str(raw_value or "")
            else:
                value = raw_value
            items.append(
                {
                    "key": field["key"],
                    "label": field["label"],
                    "fieldType": field["type"],
                    "value": value,
                }
            )
        self._server_fields_model.set_items(items)

    @Slot(str, str, "QVariant")
    def setServerField(self, category: str, key: str, value) -> None:
        if category not in SERVER_CATEGORY_DEFS:
            return
        values = self._server_values.setdefault(category, {})
        values[key] = value

    @Slot(str)
    def saveServerCategory(self, category: str) -> None:
        if category not in SERVER_CATEGORY_DEFS:
            self._set_error_message(f"未知配置分类：{category}")
            return
        payload = self._typed_server_payload(category)
        self._task_runner.submit(
            lambda: self._api_client.update_config(payload),
            on_success=lambda result: self._handle_server_save_result(category, result),
            on_error=self._set_error_message,
        )

    def _typed_server_payload(self, category: str) -> dict[str, Any]:
        current = self._server_values.get(category) or {}
        payload: dict[str, Any] = {}
        for field in SERVER_CATEGORY_DEFS[category]["fields"]:
            value = current.get(field["key"])
            payload[field["key"]] = self._coerce_server_value(field["type"], value)
        return payload

    def _coerce_server_value(self, field_type: str, value: Any) -> Any:
        if field_type == "bool":
            return bool(value)
        if field_type == "int":
            try:
                return int(value)
            except (TypeError, ValueError):
                return 0
        if field_type == "multiline":
            if isinstance(value, list):
                return value
            return [line.strip() for line in str(value or "").splitlines() if line.strip()]
        return str(value or "")

    def _handle_server_save_result(self, category: str, result: dict[str, Any]) -> None:
        message = str(result.get("message") or "配置已保存")
        self._server_status_message = message
        self.serverStatusMessageChanged.emit()
        self._set_info_message(message)
        self.loadServerCategory(category)

    @Slot(str)
    def reloadServerConfig(self, current_category: str) -> None:
        self._task_runner.submit(
            self._api_client.reload_config,
            on_success=lambda result: self._handle_reload_result(current_category, result),
            on_error=self._set_error_message,
        )

    def _handle_reload_result(self, category: str, result: dict[str, Any]) -> None:
        message = str(result.get("message") or "已从 config.yml 重新导入配置")
        self._set_info_message(message)
        self._server_status_message = message
        self.serverStatusMessageChanged.emit()
        if category in SERVER_CATEGORY_DEFS:
            self.loadServerCategory(category)

    @Slot()
    def loadRcloneConfigFile(self) -> None:
        self._task_runner.submit(
            self._load_rclone_bundle,
            on_success=self._apply_rclone_bundle,
            on_error=self._set_error_message,
        )

    def _load_rclone_bundle(self) -> dict[str, Any]:
        config_payload = self._api_client.get_rclone_config()
        remotes_payload = self._api_client.get_rclone_remotes()
        return {
            "config": config_payload,
            "remotes": remotes_payload,
        }

    def _apply_rclone_bundle(self, payload: dict[str, Any]) -> None:
        config_payload = payload.get("config") or {}
        remotes_payload = payload.get("remotes") or {}
        self._rclone_config_text = str(config_payload.get("content") or "")
        self._rclone_config_path = str(
            config_payload.get("file_path") or "/root/.config/rclone/rclone.conf"
        )
        self._rclone_remotes = list(remotes_payload.get("data") or remotes_payload.get("remotes") or [])
        self.rcloneConfigTextChanged.emit()
        self.rcloneConfigPathChanged.emit()
        self.rcloneRemotesChanged.emit()

    @Slot(str)
    def setRcloneConfigText(self, value: str) -> None:
        if value == self._rclone_config_text:
            return
        self._rclone_config_text = value
        self.rcloneConfigTextChanged.emit()

    @Slot()
    def saveRcloneConfigFile(self) -> None:
        self._task_runner.submit(
            lambda: self._api_client.save_rclone_config(self._rclone_config_text),
            on_success=lambda result: self._set_info_message(str(result.get("message") or "Rclone 配置已保存")),
            on_error=self._set_error_message,
        )

    def loadManagementSnapshot(self) -> None:
        self.loadDockerStatus()
        self.loadDockerLogs()
        self.loadSystemResources()

    @Slot()
    def loadDockerStatus(self) -> None:
        self._task_runner.submit(
            self._api_client.get_docker_status,
            on_success=self._apply_docker_status,
            on_error=self._set_error_message,
        )

    def _apply_docker_status(self, payload: dict[str, Any]) -> None:
        self._docker_status = dict(payload)
        self.dockerStatusChanged.emit()

    @Slot()
    def restartDocker(self) -> None:
        self._task_runner.submit(
            self._api_client.restart_docker,
            on_success=lambda result: self._handle_restart_docker(result),
            on_error=self._set_error_message,
        )

    def _handle_restart_docker(self, result: dict[str, Any]) -> None:
        self._set_info_message(str(result.get("message") or "容器重启命令已提交"))
        self.loadDockerStatus()
        self.loadDockerLogs()

    @Slot(int)
    def setDockerLogLines(self, value: int) -> None:
        normalized = max(20, int(value))
        if normalized == self._docker_log_lines:
            return
        self._docker_log_lines = normalized
        self.dockerLogLinesChanged.emit()

    @Slot()
    def loadDockerLogs(self) -> None:
        self._task_runner.submit(
            lambda: self._api_client.get_docker_logs(lines=self._docker_log_lines),
            on_success=self._apply_docker_logs,
            on_error=self._set_error_message,
        )

    def _apply_docker_logs(self, payload: dict[str, Any]) -> None:
        self._docker_logs = str(payload.get("logs") or "")
        self.dockerLogsChanged.emit()

    @Slot()
    def clearDockerLogs(self) -> None:
        self._docker_logs = ""
        self.dockerLogsChanged.emit()

    @Slot()
    def loadSystemResources(self) -> None:
        self._resource_refresh_scheduled = False
        self._task_runner.submit(
            self._api_client.get_system_resources,
            on_success=self._apply_resources,
            on_error=self._set_error_message,
        )

    def _apply_resources(self, payload: dict[str, Any]) -> None:
        data = (payload.get("data") or {}) if isinstance(payload, dict) else {}
        cpu = data.get("cpu") or {}
        memory = data.get("memory") or {}
        disk = data.get("disk") or {}
        self._resource_cards = [
            {
                "title": "CPU",
                "value": f"{float(cpu.get('percent') or 0):.1f}%",
                "caption": "系统处理器占用",
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
                "title": "硬盘",
                "value": f"{float(disk.get('percent') or 0):.1f}%",
                "caption": f"{format_bytes(disk.get('used'))} / {format_bytes(disk.get('total'))}",
                "tone": self._resource_tone(float(disk.get("percent") or 0)),
                "percent": float(disk.get("percent") or 0),
            },
        ]
        self.resourceCardsChanged.emit()

    def _resource_tone(self, percent: float) -> str:
        if percent >= 85:
            return "danger"
        if percent >= 65:
            return "warning"
        return "success"

    @Slot()
    def loadAppLogFiles(self) -> None:
        self._task_runner.submit(
            self._api_client.get_log_files,
            on_success=self._apply_log_files,
            on_error=self._set_error_message,
        )

    def _apply_log_files(self, payload: dict[str, Any]) -> None:
        files = list(payload.get("files") or [])
        self._log_files_model.set_items(
            [
                {
                    "name": str(item.get("name") or ""),
                    "size": int(item.get("size") or 0),
                    "sizeText": format_bytes(item.get("size")),
                    "modified": str(item.get("modified") or ""),
                }
                for item in files
            ]
        )
        if not self._selected_log_file and files:
            self._selected_log_file = str(files[0].get("name") or "")
            self.selectedLogFileChanged.emit()
        self.loadAppLogs()

    @Slot(str)
    def setSelectedLogFile(self, value: str) -> None:
        if value == self._selected_log_file:
            return
        self._selected_log_file = value
        self.selectedLogFileChanged.emit()

    @Slot(str)
    def setLogLevel(self, value: str) -> None:
        if value == self._log_level:
            return
        self._log_level = value
        self.logLevelChanged.emit()

    @Slot(str)
    def setLogKeyword(self, value: str) -> None:
        if value == self._log_keyword:
            return
        self._log_keyword = value
        self.logKeywordChanged.emit()

    @Slot(int)
    def setLogTailCount(self, value: int) -> None:
        normalized = max(50, int(value))
        if normalized == self._log_tail_count:
            return
        self._log_tail_count = normalized
        self.logTailCountChanged.emit()

    @Slot()
    def loadAppLogs(self) -> None:
        self._task_runner.submit(
            lambda: self._api_client.get_log_content(
                file=self._selected_log_file or None,
                tail=self._log_tail_count,
                level=self._log_level or None,
                keyword=self._log_keyword or None,
            ),
            on_success=self._apply_app_logs,
            on_error=self._set_error_message,
        )

    def _apply_app_logs(self, payload: dict[str, Any]) -> None:
        lines = list(payload.get("lines") or [])
        self._app_log_text = "\n".join(str(line) for line in lines)
        self._app_log_summary = f"{len(lines)} 行日志"
        self.appLogTextChanged.emit()
        self.appLogSummaryChanged.emit()

    @Slot()
    def clearAppLogDisplay(self) -> None:
        self._app_log_text = ""
        self._app_log_summary = "已清空显示内容"
        self.appLogTextChanged.emit()
        self.appLogSummaryChanged.emit()

    @Slot()
    def downloadSelectedLogFile(self) -> None:
        if not self._selected_log_file:
            return
        destination = logs_root() / self._selected_log_file
        self._task_runner.submit(
            lambda: self._api_client.download_log_file(self._selected_log_file, destination),
            on_success=lambda path: self._handle_log_download(path),
            on_error=self._set_error_message,
        )

    def _handle_log_download(self, path) -> None:
        self._set_info_message(f"日志已下载到 {path}")
        self._local_runtime_service.show_local_file_in_folder(str(path))

    serverBaseUrl = Property(str, get_server_base_url, notify=serverBaseUrlChanged)
    proxyEnabled = Property(bool, get_proxy_enabled, notify=proxyEnabledChanged)
    proxyUrl = Property(str, get_proxy_url, notify=proxyUrlChanged)
    downloadDir = Property(str, get_download_dir, notify=downloadDirChanged)
    maxConcurrentDownloads = Property(int, get_max_concurrent_downloads, notify=maxConcurrentDownloadsChanged)
    threadsPerDownload = Property(int, get_threads_per_download, notify=threadsPerDownloadChanged)

    updateState = Property(str, get_update_state, notify=updateStateChanged)
    updateNotes = Property(str, get_update_notes, notify=updateNotesChanged)
    manualUrl = Property(str, get_manual_url, notify=manualUrlChanged)
    updateVersion = Property(str, get_update_version, notify=updateVersionChanged)
    updateAvailable = Property(bool, get_update_available, notify=updateAvailableChanged)
    canInstallUpdate = Property(bool, get_can_install_update, notify=canInstallUpdateChanged)
    updateProgressPercent = Property(int, get_update_progress_percent, notify=updateProgressPercentChanged)

    serverCategories = Property("QVariantList", get_server_categories, notify=serverCategoriesChanged)
    serverStatusMessage = Property(str, get_server_status_message, notify=serverStatusMessageChanged)
    serverFieldsModel = Property(QObject, get_server_fields_model, constant=True)

    rcloneConfigText = Property(str, get_rclone_config_text, notify=rcloneConfigTextChanged)
    rcloneConfigPath = Property(str, get_rclone_config_path, notify=rcloneConfigPathChanged)
    rcloneRemotes = Property("QVariantList", get_rclone_remotes, notify=rcloneRemotesChanged)

    dockerStatus = Property("QVariantMap", get_docker_status, notify=dockerStatusChanged)
    dockerLogs = Property(str, get_docker_logs, notify=dockerLogsChanged)
    dockerLogLines = Property(int, get_docker_log_lines, notify=dockerLogLinesChanged)
    resourceCards = Property("QVariantList", get_resource_cards, notify=resourceCardsChanged)

    logFilesModel = Property(QObject, get_log_files_model, constant=True)
    appLogText = Property(str, get_app_log_text, notify=appLogTextChanged)
    appLogSummary = Property(str, get_app_log_summary, notify=appLogSummaryChanged)
    selectedLogFile = Property(str, get_selected_log_file, notify=selectedLogFileChanged)
    logLevel = Property(str, get_log_level, notify=logLevelChanged)
    logKeyword = Property(str, get_log_keyword, notify=logKeywordChanged)
    logTailCount = Property(int, get_log_tail_count, notify=logTailCountChanged)
