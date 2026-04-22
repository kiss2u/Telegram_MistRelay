from __future__ import annotations

import base64
import builtins
import hashlib
import json
import shutil
import sys
import tempfile
import unittest
from pathlib import Path
from unittest.mock import patch

import httpx


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from mistrelay_qt.models import UpdateInfo
from mistrelay_qt.services.update_service import UpdateService, compare_versions


class UpdateServiceReleaseFeedTests(unittest.TestCase):
    def test_compare_versions_handles_beta_patch_numbers(self) -> None:
        self.assertGreater(compare_versions("0.2.15-beta.10", "0.2.15-beta.2"), 0)

    def test_select_release_assets_uses_latest_matching_tag_prefix(self) -> None:
        service = UpdateService(
            current_version="0.2.15-beta.1",
            manifest_url="",
            signature_url="",
            release_feed_url="https://api.github.com/repos/example/project/releases?per_page=30",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )

        manifest_url, signature_url = service._select_release_assets(
            [
                {
                    "tag_name": "desktop-v0.1.0",
                    "draft": False,
                    "assets": [],
                },
                {
                    "tag_name": "desktop-qt-v0.2.15-beta.2",
                    "draft": False,
                    "assets": [
                        {
                            "name": "qt-latest.json",
                            "browser_download_url": "https://example.invalid/qt-latest.json",
                        },
                        {
                            "name": "qt-latest.json.sig",
                            "browser_download_url": "https://example.invalid/qt-latest.json.sig",
                        },
                    ],
                },
                {
                    "tag_name": "desktop-qt-v0.2.14-beta.9",
                    "draft": False,
                    "assets": [
                        {
                            "name": "qt-latest.json",
                            "browser_download_url": "https://example.invalid/older-qt-latest.json",
                        },
                        {
                            "name": "qt-latest.json.sig",
                            "browser_download_url": "https://example.invalid/older-qt-latest.json.sig",
                        },
                    ],
                },
            ]
        )

        self.assertEqual(manifest_url, "https://example.invalid/qt-latest.json")
        self.assertEqual(signature_url, "https://example.invalid/qt-latest.json.sig")

    def test_select_release_assets_fails_when_release_assets_are_missing(self) -> None:
        service = UpdateService(
            current_version="0.2.15-beta.1",
            manifest_url="",
            signature_url="",
            release_feed_url="https://api.github.com/repos/example/project/releases?per_page=30",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )

        with self.assertRaisesRegex(RuntimeError, "qt-latest.json"):
            service._select_release_assets(
                [
                    {
                        "tag_name": "desktop-qt-v0.2.15-beta.2",
                        "draft": False,
                        "assets": [],
                    }
                ]
            )


class UpdateServiceNetworkTests(unittest.TestCase):
    def _patch_http_client(self, transport: httpx.MockTransport, captured: list[dict[str, object]]):
        original_client = httpx.Client

        def factory(*args, **kwargs):
            captured.append(dict(kwargs))
            kwargs["transport"] = transport
            return original_client(*args, **kwargs)

        return patch("httpx.Client", side_effect=factory)

    def test_check_for_updates_follows_release_asset_redirects(self) -> None:
        release_feed_url = "https://api.github.com/repos/example/project/releases?per_page=30"
        manifest_url = "https://example.invalid/qt-latest.json"
        signature_url = "https://example.invalid/qt-latest.json.sig"
        installer_url = "https://example.invalid/mistrelay-setup.exe"

        service = UpdateService(
            current_version="0.2.15-beta.5",
            manifest_url="",
            signature_url="",
            release_feed_url=release_feed_url,
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )

        manifest_payload = {
            "version": "0.2.15-beta.6",
            "notes": "redirect test",
            "platforms": {
                service._platform_key(): {
                    "url": installer_url,
                    "sha256": "deadbeef",
                    "size": 10,
                }
            },
        }

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == release_feed_url:
                return httpx.Response(
                    200,
                    json=[
                        {
                            "tag_name": "desktop-qt-v0.2.15-beta.6",
                            "draft": False,
                            "assets": [
                                {
                                    "name": "qt-latest.json",
                                    "browser_download_url": manifest_url,
                                },
                                {
                                    "name": "qt-latest.json.sig",
                                    "browser_download_url": signature_url,
                                },
                            ],
                        }
                    ],
                    request=request,
                )
            if url == manifest_url:
                return httpx.Response(
                    302,
                    headers={"Location": "https://cdn.example.invalid/qt-latest.json"},
                    request=request,
                )
            if url == "https://cdn.example.invalid/qt-latest.json":
                return httpx.Response(
                    200,
                    content=json.dumps(manifest_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    request=request,
                )
            return httpx.Response(404, request=request)

        captured: list[dict[str, object]] = []
        with self._patch_http_client(httpx.MockTransport(handler), captured):
            info = service.check_for_updates()

        self.assertTrue(captured)
        self.assertTrue(captured[0]["follow_redirects"])
        self.assertTrue(info.available)
        self.assertEqual(info.version, "0.2.15-beta.6")
        self.assertEqual(info.manual_url, installer_url)

    def test_check_for_updates_wraps_release_feed_http_errors(self) -> None:
        release_feed_url = "https://api.github.com/repos/example/project/releases?per_page=30"
        service = UpdateService(
            current_version="0.2.15-beta.5",
            manifest_url="",
            signature_url="",
            release_feed_url=release_feed_url,
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(403, request=request)

        with self._patch_http_client(httpx.MockTransport(handler), []):
            with self.assertRaisesRegex(RuntimeError, r"获取 Qt 发布列表失败：HTTP 403"):
                service.check_for_updates()

    def test_check_for_updates_wraps_signature_download_http_errors(self) -> None:
        manifest_url = "https://example.invalid/qt-latest.json"
        signature_url = "https://example.invalid/qt-latest.json.sig"
        service = UpdateService(
            current_version="0.2.15-beta.5",
            manifest_url=manifest_url,
            signature_url=signature_url,
            release_feed_url="",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="AAAA",
        )

        manifest_payload = {
            "version": "0.2.15-beta.6",
            "platforms": {
                service._platform_key(): {
                    "url": "https://example.invalid/mistrelay-setup.exe",
                    "sha256": "deadbeef",
                    "size": 10,
                }
            },
        }

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == manifest_url:
                return httpx.Response(
                    200,
                    content=json.dumps(manifest_payload).encode("utf-8"),
                    headers={"Content-Type": "application/json"},
                    request=request,
                )
            if url == signature_url:
                return httpx.Response(503, request=request)
            return httpx.Response(404, request=request)

        with self._patch_http_client(httpx.MockTransport(handler), []):
            with self.assertRaisesRegex(RuntimeError, r"下载更新签名失败：HTTP 503"):
                service.check_for_updates()

    def test_download_update_follows_release_asset_redirects(self) -> None:
        installer_url = "https://example.invalid/mistrelay-desktop-qt-v0.2.15-beta.6-setup.exe"
        installer_bytes = b"mistrelay-installer"
        digest = hashlib.sha256(installer_bytes).hexdigest()
        service = UpdateService(
            current_version="0.2.15-beta.5",
            manifest_url="",
            signature_url="",
            release_feed_url="",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )
        info = UpdateInfo(
            available=True,
            version="0.2.15-beta.6",
            download_url=installer_url,
            manual_url=installer_url,
            sha256=digest,
            size=len(installer_bytes),
        )

        def handler(request: httpx.Request) -> httpx.Response:
            url = str(request.url)
            if url == installer_url:
                return httpx.Response(
                    302,
                    headers={"Location": "https://cdn.example.invalid/mistrelay-setup.exe"},
                    request=request,
                )
            if url == "https://cdn.example.invalid/mistrelay-setup.exe":
                return httpx.Response(
                    200,
                    content=installer_bytes,
                    headers={"Content-Length": str(len(installer_bytes))},
                    request=request,
                )
            return httpx.Response(404, request=request)

        captured: list[dict[str, object]] = []
        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("mistrelay_qt.services.update_service.updates_root", return_value=Path(temp_dir)):
                with self._patch_http_client(httpx.MockTransport(handler), captured):
                    downloaded = service.download_update(info)

            self.assertTrue(captured)
            self.assertTrue(captured[0]["follow_redirects"])
            self.assertTrue(downloaded.installer_path.exists())
            self.assertEqual(downloaded.installer_path.read_bytes(), installer_bytes)

    def test_download_update_wraps_http_errors(self) -> None:
        installer_url = "https://example.invalid/mistrelay-desktop-qt-v0.2.15-beta.6-setup.exe"
        service = UpdateService(
            current_version="0.2.15-beta.5",
            manifest_url="",
            signature_url="",
            release_feed_url="",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )
        info = UpdateInfo(
            available=True,
            version="0.2.15-beta.6",
            download_url=installer_url,
            manual_url=installer_url,
            sha256=hashlib.sha256(b"payload").hexdigest(),
            size=7,
        )

        def handler(request: httpx.Request) -> httpx.Response:
            return httpx.Response(503, request=request)

        with tempfile.TemporaryDirectory() as temp_dir:
            with patch("mistrelay_qt.services.update_service.updates_root", return_value=Path(temp_dir)):
                with self._patch_http_client(httpx.MockTransport(handler), []):
                    with self.assertRaisesRegex(RuntimeError, r"下载安装包失败：HTTP 503"):
                        service.download_update(info)


class UpdateServiceSignatureVerificationTests(unittest.TestCase):
    def _make_signed_manifest(self) -> tuple[UpdateService, bytes, str]:
        from nacl.signing import SigningKey

        manifest_bytes = json.dumps(
            {
                "version": "0.2.15-beta.8",
                "platforms": {
                    "windows-x86_64": {
                        "url": "https://example.invalid/setup.exe",
                        "sha256": "deadbeef",
                        "size": 42,
                    }
                },
            }
        ).encode("utf-8")
        signing_key = SigningKey.generate()
        verify_key = base64.b64encode(bytes(signing_key.verify_key)).decode("ascii")
        signature = base64.b64encode(signing_key.sign(manifest_bytes).signature).decode("ascii")
        service = UpdateService(
            current_version="0.2.15-beta.7",
            manifest_url="",
            signature_url="https://example.invalid/qt-latest.json.sig",
            release_feed_url="",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key=verify_key,
        )
        return service, manifest_bytes, signature

    def test_verify_manifest_accepts_valid_signature(self) -> None:
        service, manifest_bytes, signature = self._make_signed_manifest()

        with patch.object(service, "_get_response", return_value=unittest.mock.Mock(text=signature)):
            self.assertTrue(service._verify_manifest(unittest.mock.Mock(), manifest_bytes, service._signature_url))

    def test_verify_manifest_reports_missing_pynacl_dependency(self) -> None:
        service, manifest_bytes, signature = self._make_signed_manifest()
        original_import = builtins.__import__

        def failing_import(name, globals=None, locals=None, fromlist=(), level=0):
            if name == "nacl.signing":
                raise ModuleNotFoundError("No module named 'nacl.signing'", name="nacl.signing")
            return original_import(name, globals, locals, fromlist, level)

        with patch.object(service, "_get_response", return_value=unittest.mock.Mock(text=signature)):
            with patch("builtins.__import__", side_effect=failing_import):
                with self.assertRaisesRegex(RuntimeError, "缺少 PyNaCl 依赖，无法校验更新签名"):
                    service._verify_manifest(unittest.mock.Mock(), manifest_bytes, service._signature_url)

    def test_verify_manifest_reports_missing_runtime_dependency(self) -> None:
        service, manifest_bytes, signature = self._make_signed_manifest()
        from nacl.signing import VerifyKey

        with patch.object(service, "_get_response", return_value=unittest.mock.Mock(text=signature)):
            with patch.object(
                VerifyKey,
                "verify",
                side_effect=ModuleNotFoundError("No module named '_cffi_backend'", name="_cffi_backend"),
            ):
                with self.assertRaisesRegex(RuntimeError, "更新验签依赖缺失：_cffi_backend"):
                    service._verify_manifest(unittest.mock.Mock(), manifest_bytes, service._signature_url)


class UpdateServiceWindowsInstallerScriptTests(unittest.TestCase):
    def test_write_windows_update_script_restarts_only_after_successful_install(self) -> None:
        service = UpdateService(
            current_version="0.2.15-beta.8",
            manifest_url="",
            signature_url="",
            release_feed_url="",
            release_tag_prefix="desktop-qt-v",
            manifest_asset_name="qt-latest.json",
            signature_asset_name="qt-latest.json.sig",
            verify_key="",
        )

        script_path = service._write_windows_update_script(
            installer_path=Path(r"C:\Temp\mistrelay-setup.exe"),
            app_executable=Path(r"C:\Users\demo\AppData\Local\Programs\MistRelay Desktop Qt\MistRelay Desktop Qt.exe"),
            target_pid=4321,
        )
        self.addCleanup(shutil.rmtree, script_path.parent, True)

        script = script_path.read_text(encoding="utf-8")
        self.assertIn("$installerProcess = Start-Process -FilePath $installer -ArgumentList '/S' -PassThru -Wait", script)
        self.assertIn("if ($installerProcess.ExitCode -ne 0) { exit $installerProcess.ExitCode }", script)
        self.assertIn("if (Test-Path $appExe) { Start-Process -FilePath $appExe }", script)


if __name__ == "__main__":
    unittest.main()
