from __future__ import annotations

import sys
from dataclasses import dataclass
from pathlib import Path

from PySide6.QtCore import QUrl
from PySide6.QtGui import QIcon
from PySide6.QtQml import QQmlApplicationEngine
from PySide6.QtQuickControls2 import QQuickStyle
from PySide6.QtWidgets import QApplication

from .constants import (
    APP_NAME,
    DEFAULT_WINDOW_HEIGHT,
    DEFAULT_WINDOW_WIDTH,
    MIN_WINDOW_HEIGHT,
    MIN_WINDOW_WIDTH,
    ORGANIZATION_DOMAIN,
    ORGANIZATION_NAME,
)
from .runtime import release_metadata, resolve_resource
from .services import ApiClient, ConfigService, LocalRuntimeService, UpdateService, WebsocketService
from .task_runner import TaskRunner
from .viewmodels import (
    AppViewModel,
    DashboardViewModel,
    DownloadsViewModel,
    DriveViewModel,
    LoginViewModel,
    SettingsViewModel,
    UpdateViewModel,
)


@dataclass(slots=True)
class ApplicationContext:
    local_runtime_service: LocalRuntimeService
    app_view_model: AppViewModel
    login_view_model: LoginViewModel
    dashboard_view_model: DashboardViewModel
    downloads_view_model: DownloadsViewModel
    drive_view_model: DriveViewModel
    settings_view_model: SettingsViewModel
    update_view_model: UpdateViewModel


def app_version() -> str:
    return release_metadata().version


def build_engine(application: QApplication) -> QQmlApplicationEngine:
    engine = QQmlApplicationEngine(application)
    qml_root = Path(resolve_resource("mistrelay_qt", "qml"))
    engine.addImportPath(str(qml_root))
    return engine


def build_application_context() -> ApplicationContext:
    config_service = ConfigService()
    local_runtime_service = LocalRuntimeService(config_service=config_service)
    api_client = ApiClient(config_service)
    websocket_service = WebsocketService(config_service)
    task_runner = TaskRunner()
    update_service = UpdateService(
        current_version=app_version(),
        config_service=config_service,
    )

    app_view_model = AppViewModel(
        config_service=config_service,
        api_client=api_client,
        websocket_service=websocket_service,
        task_runner=task_runner,
    )
    login_view_model = LoginViewModel(
        config_service=config_service,
        api_client=api_client,
        task_runner=task_runner,
    )
    dashboard_view_model = DashboardViewModel(api_client=api_client, task_runner=task_runner)
    downloads_view_model = DownloadsViewModel(
        api_client=api_client,
        local_runtime_service=local_runtime_service,
        task_runner=task_runner,
    )
    drive_view_model = DriveViewModel(
        api_client=api_client,
        local_runtime_service=local_runtime_service,
        task_runner=task_runner,
    )
    update_view_model = UpdateViewModel(
        update_service=update_service,
        local_runtime_service=local_runtime_service,
        task_runner=task_runner,
    )
    settings_view_model = SettingsViewModel(
        api_client=api_client,
        config_service=config_service,
        local_runtime_service=local_runtime_service,
        update_service=update_service,
        task_runner=task_runner,
    )

    app_view_model.register_refreshers(
        {
            "dashboard": dashboard_view_model.refresh,
            "downloads": downloads_view_model.refresh,
            "drive": drive_view_model.refresh,
            "settings": settings_view_model.bootstrap,
        }
    )
    login_view_model.loginSucceeded.connect(app_view_model.loginSucceeded)
    app_view_model.register_status_consumers(
        {
            "dashboard": dashboard_view_model.consume_status_event,
            "downloads": downloads_view_model.consume_status_event,
            "drive": drive_view_model.consume_status_event,
            "settings": settings_view_model.consume_status_event,
        }
    )
    websocket_service.statusReceived.connect(app_view_model.handle_status_message)

    return ApplicationContext(
        local_runtime_service=local_runtime_service,
        app_view_model=app_view_model,
        login_view_model=login_view_model,
        dashboard_view_model=dashboard_view_model,
        downloads_view_model=downloads_view_model,
        drive_view_model=drive_view_model,
        settings_view_model=settings_view_model,
        update_view_model=update_view_model,
    )


def attach_context(engine: QQmlApplicationEngine, context: ApplicationContext) -> None:
    root_context = engine.rootContext()
    root_context.setContextProperty("appVersion", app_version())
    root_context.setContextProperty("appViewModel", context.app_view_model)
    root_context.setContextProperty("loginViewModel", context.login_view_model)
    root_context.setContextProperty("dashboardViewModel", context.dashboard_view_model)
    root_context.setContextProperty("downloadsViewModel", context.downloads_view_model)
    root_context.setContextProperty("driveViewModel", context.drive_view_model)
    root_context.setContextProperty("settingsViewModel", context.settings_view_model)
    root_context.setContextProperty("updateViewModel", context.update_view_model)


def main() -> int:
    QQuickStyle.setStyle("Basic")

    application = QApplication(sys.argv)
    application.setApplicationName(APP_NAME)
    application.setOrganizationName(ORGANIZATION_NAME)
    application.setOrganizationDomain(ORGANIZATION_DOMAIN)

    icon_path = resolve_resource("desktop", "icons", "icon.png")
    if icon_path.exists():
        application.setWindowIcon(QIcon(str(icon_path)))

    context = build_application_context()

    engine = build_engine(application)
    attach_context(engine, context)

    main_qml = resolve_resource("mistrelay_qt", "qml", "Main.qml")
    engine.load(QUrl.fromLocalFile(str(main_qml)))

    if not engine.rootObjects():
        return 1

    root = engine.rootObjects()[0]
    root.setWidth(DEFAULT_WINDOW_WIDTH)
    root.setHeight(DEFAULT_WINDOW_HEIGHT)
    root.setMinimumWidth(MIN_WINDOW_WIDTH)
    root.setMinimumHeight(MIN_WINDOW_HEIGHT)

    context.app_view_model.bootstrap()
    application.aboutToQuit.connect(context.drive_view_model.closePreview)
    application.aboutToQuit.connect(context.settings_view_model.shutdown)
    application.aboutToQuit.connect(context.local_runtime_service.shutdown)
    return application.exec()
