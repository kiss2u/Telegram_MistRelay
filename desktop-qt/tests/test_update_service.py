from __future__ import annotations

import sys
import unittest
from pathlib import Path


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

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


if __name__ == "__main__":
    unittest.main()
