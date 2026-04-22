from __future__ import annotations

from PySide6.QtCore import Property, Signal, Slot

from ..task_runner import TaskRunner
from .base import BaseViewModel


class LoginViewModel(BaseViewModel):
    usernameChanged = Signal()
    passwordChanged = Signal()
    serverBaseUrlChanged = Signal()
    loginSucceeded = Signal(str)

    def __init__(self, *, config_service, api_client, task_runner: TaskRunner) -> None:
        super().__init__()
        self._config_service = config_service
        self._api_client = api_client
        self._task_runner = task_runner
        self._username = ""
        self._password = ""
        self._server_base_url = self._config_service.config.server_base_url

    def get_username(self) -> str:
        return self._username

    def get_password(self) -> str:
        return self._password

    def get_server_base_url(self) -> str:
        return self._server_base_url

    @Slot(str)
    def setUsername(self, value: str) -> None:
        value = value.strip()
        if self._username == value:
            return
        self._username = value
        self.usernameChanged.emit()

    @Slot(str)
    def setPassword(self, value: str) -> None:
        if self._password == value:
            return
        self._password = value
        self.passwordChanged.emit()

    @Slot(str)
    def setServerBaseUrl(self, value: str) -> None:
        normalized = value.strip().rstrip("/")
        if self._server_base_url == normalized:
            return
        self._server_base_url = normalized
        self.serverBaseUrlChanged.emit()

    @Slot()
    def submitLogin(self) -> None:
        if self._busy:
            return
        if not self._server_base_url:
            self._set_error_message("请先填写服务端地址")
            return
        if not self._username or not self._password:
            self._set_error_message("请输入用户名和密码")
            return

        self._set_busy(True)
        self._set_error_message("")
        self._set_info_message("正在连接服务端并校验账号")
        self._config_service.update_server_base_url(self._server_base_url)

        self._task_runner.submit(
            lambda: self._api_client.login(self._username, self._password),
            on_success=self._handle_login_success,
            on_error=self._handle_login_error,
        )

    def _handle_login_success(self, payload: dict) -> None:
        self._set_busy(False)
        token = str(payload.get("token") or "")
        user = payload.get("user") or {}
        self._config_service.save_user_session(
            server_base_url=self._server_base_url,
            token=token,
            user=user,
        )
        self._password = ""
        self.passwordChanged.emit()
        self._set_info_message("登录成功，正在进入桌面客户端")
        self.loginSucceeded.emit(str(user.get("username") or self._username))

    def _handle_login_error(self, message: str) -> None:
        self._set_busy(False)
        self._set_error_message(message)
        self._set_info_message("")

    username = Property(str, get_username, notify=usernameChanged)
    password = Property(str, get_password, notify=passwordChanged)
    serverBaseUrl = Property(str, get_server_base_url, notify=serverBaseUrlChanged)
