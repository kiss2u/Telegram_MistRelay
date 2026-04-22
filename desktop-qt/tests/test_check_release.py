from __future__ import annotations

import os
import sys
import unittest
from pathlib import Path
from unittest import mock


PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from scripts import check_release


class CheckReleaseVerifyKeyTests(unittest.TestCase):
    def test_resolve_verify_key_uses_version_payload_when_env_is_missing(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(
                check_release.resolve_verify_key({"verify_key": "repo-public-key"}),
                "repo-public-key",
            )

    def test_resolve_verify_key_prefers_explicit_env_override(self) -> None:
        with mock.patch.dict(
            os.environ,
            {"QT_UPDATE_VERIFY_KEY": "env-public-key"},
            clear=True,
        ):
            self.assertEqual(
                check_release.resolve_verify_key({"verify_key": "repo-public-key"}),
                "env-public-key",
            )

    def test_resolve_verify_key_prefers_mistrelay_env_override(self) -> None:
        with mock.patch.dict(
            os.environ,
            {
                "QT_UPDATE_VERIFY_KEY": "generic-env-public-key",
                "MISTRELAY_QT_UPDATE_VERIFY_KEY": "mistrelay-env-public-key",
            },
            clear=True,
        ):
            self.assertEqual(
                check_release.resolve_verify_key({"verify_key": "repo-public-key"}),
                "mistrelay-env-public-key",
            )

    def test_missing_verify_key_message_mentions_env_and_version_file(self) -> None:
        with mock.patch.dict(os.environ, {}, clear=True):
            self.assertEqual(check_release.resolve_verify_key({"verify_key": ""}), "")
        self.assertIn("MISTRELAY_QT_UPDATE_VERIFY_KEY", check_release.missing_verify_key_message())
        self.assertIn("desktop-qt/version.json", check_release.missing_verify_key_message())


if __name__ == "__main__":
    unittest.main()
