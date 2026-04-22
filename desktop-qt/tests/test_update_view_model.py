from __future__ import annotations

import importlib.util
import sys
import unittest
from pathlib import Path
from unittest.mock import patch


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistrelay_qt.models import DownloadedUpdate, UpdateInfo


HAS_PYSIDE6 = importlib.util.find_spec("PySide6") is not None

if HAS_PYSIDE6:
    from PySide6.QtCore import QCoreApplication

    from mistrelay_qt.viewmodels.update import UpdateViewModel


class ImmediateTaskRunner:
    def submit(self, fn, *, on_success=None, on_error=None) -> None:
        try:
            result = fn()
        except Exception as exc:  # pragma: no cover - test relay only
            if on_error:
                on_error(str(exc))
        else:
            if on_success:
                on_success(result)


class StubUpdateService:
    def __init__(self, results: list[UpdateInfo | Exception]) -> None:
        self._results = list(results)
        self.check_calls = 0
        self.download_calls: list[str] = []
        self.install_calls: list[str] = []

    def check_for_updates(self) -> UpdateInfo:
        self.check_calls += 1
        next_result = self._results.pop(0)
        if isinstance(next_result, Exception):
            raise next_result
        return next_result

    def download_update(self, info: UpdateInfo, *, on_progress=None) -> DownloadedUpdate:
        self.download_calls.append(info.version)
        if on_progress:
            on_progress(64, 128, False)
            on_progress(128, 128, True)
        return DownloadedUpdate(
            version=info.version,
            installer_path=Path("/tmp") / f"{info.version}.exe",
            download_url=info.download_url or "https://example.invalid/setup.exe",
            sha256=info.sha256 or "deadbeef",
            size=128,
        )

    def install_update(self, downloaded: DownloadedUpdate) -> None:
        self.install_calls.append(downloaded.version)


class StubLocalRuntimeService:
    def __init__(self) -> None:
        self.opened_urls: list[str] = []

    def open_external_url(self, url: str) -> None:
        self.opened_urls.append(url)


@unittest.skipUnless(HAS_PYSIDE6, "requires PySide6")
class UpdateViewModelTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        cls._app = QCoreApplication.instance() or QCoreApplication([])

    def build_view_model(self, results: list[UpdateInfo | Exception]) -> tuple[UpdateViewModel, StubUpdateService]:
        update_service = StubUpdateService(results)
        view_model = UpdateViewModel(
            update_service=update_service,
            local_runtime_service=StubLocalRuntimeService(),
            task_runner=ImmediateTaskRunner(),
        )
        return view_model, update_service

    def test_startup_check_runs_only_once(self) -> None:
        view_model, update_service = self.build_view_model(
            [
                UpdateInfo(available=False, message="当前已是最新版本"),
                UpdateInfo(available=False, message="不应被第二次消费"),
            ]
        )

        view_model.startupCheck()
        view_model.startupCheck()

        self.assertEqual(update_service.check_calls, 1)
        self.assertFalse(view_model.promptVisible)

    def test_startup_check_shows_prompt_for_installable_update(self) -> None:
        view_model, _update_service = self.build_view_model(
            [
                UpdateInfo(
                    available=True,
                    version="0.2.15-beta.6",
                    installable=True,
                    message="发现新版本 v0.2.15-beta.6",
                    notes="修复启动热更",
                    download_url="https://example.invalid/setup.exe",
                )
            ]
        )

        view_model.startupCheck()

        self.assertTrue(view_model.promptVisible)
        self.assertTrue(view_model.updateAvailable)
        self.assertTrue(view_model.canInstallUpdate)
        self.assertIn("等待确认安装", view_model.updateState)

    def test_manual_check_does_not_open_prompt(self) -> None:
        view_model, _update_service = self.build_view_model(
            [
                UpdateInfo(
                    available=True,
                    version="0.2.15-beta.6",
                    installable=True,
                    message="发现新版本 v0.2.15-beta.6",
                )
            ]
        )

        view_model.checkForUpdates()

        self.assertFalse(view_model.promptVisible)
        self.assertTrue(view_model.updateAvailable)
        self.assertTrue(view_model.canInstallUpdate)

    def test_install_update_downloads_and_schedules_restart(self) -> None:
        view_model, update_service = self.build_view_model(
            [
                UpdateInfo(
                    available=True,
                    version="0.2.15-beta.6",
                    installable=True,
                    message="发现新版本 v0.2.15-beta.6",
                    download_url="https://example.invalid/setup.exe",
                )
            ]
        )
        view_model.startupCheck()

        with patch("mistrelay_qt.viewmodels.update.QTimer.singleShot") as single_shot:
            view_model.installUpdate()

        self.assertEqual(update_service.download_calls, ["0.2.15-beta.6"])
        self.assertEqual(update_service.install_calls, ["0.2.15-beta.6"])
        self.assertIn("正在静默安装并重启", view_model.updateState)
        single_shot.assert_called_once()

    def test_startup_check_failure_does_not_open_prompt(self) -> None:
        view_model, _update_service = self.build_view_model([RuntimeError("network down")])

        view_model.startupCheck()

        self.assertFalse(view_model.promptVisible)
        self.assertIn("更新失败", view_model.updateState)


if __name__ == "__main__":
    unittest.main()
