from __future__ import annotations

import argparse
import compileall
import json
import os
import re
import unittest
from pathlib import Path


SEMVER_RE = re.compile(r"^[0-9]+\.[0-9]+\.[0-9]+([-.+][0-9A-Za-z.-]+)?$")


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Local pre-release checks for desktop-qt")
    parser.add_argument("--require-update-key", action="store_true")
    return parser.parse_args()


def resolve_verify_key(payload: dict[str, object]) -> str:
    return (
        os.getenv("MISTRELAY_QT_UPDATE_VERIFY_KEY")
        or os.getenv("QT_UPDATE_VERIFY_KEY")
        or str(payload.get("verify_key") or "")
    ).strip()


def missing_verify_key_message() -> str:
    return (
        "missing update verify key: set MISTRELAY_QT_UPDATE_VERIFY_KEY or "
        "QT_UPDATE_VERIFY_KEY, or populate desktop-qt/version.json verify_key"
    )


def main() -> int:
    args = parse_args()
    root = Path(__file__).resolve().parents[1]
    payload = json.loads((root / "version.json").read_text(encoding="utf-8"))
    version = str(payload.get("version") or "")
    channel = str(payload.get("channel") or "dev")
    manifest_url = str(payload.get("manifest_url") or "").strip()
    release_feed_url = str(payload.get("release_feed_url") or "").strip()
    release_tag_prefix = str(payload.get("release_tag_prefix") or "").strip()
    if not SEMVER_RE.fullmatch(version):
        raise SystemExit(f"invalid version in version.json: {version}")
    if not manifest_url and not release_feed_url:
        raise SystemExit("version.json must define manifest_url or release_feed_url")
    if release_feed_url and not release_tag_prefix:
        raise SystemExit("version.json is missing release_tag_prefix for release_feed_url mode")
    if (
        channel == "beta"
        and not release_feed_url
        and "/releases/latest/download/" in manifest_url
    ):
        raise SystemExit(
            "beta channel cannot rely on GitHub releases/latest/download; use release_feed_url"
        )

    verify_key = resolve_verify_key(payload)
    if args.require_update_key and not verify_key:
        raise SystemExit(missing_verify_key_message())

    required_paths = [
        root / "main.py",
        root / "mistrelay_qt" / "qml" / "Main.qml",
        root / "scripts" / "build_windows.py",
    ]
    for path in required_paths:
        if not path.exists():
            raise SystemExit(f"missing required file: {path}")

    if not compileall.compile_dir(
        str(root / "mistrelay_qt"),
        quiet=1,
        force=True,
    ):
        raise SystemExit("compileall reported syntax errors")

    tests_root = root / "tests"
    if tests_root.exists():
        suite = unittest.defaultTestLoader.discover(str(tests_root))
        result = unittest.TextTestRunner(verbosity=1).run(suite)
        if not result.wasSuccessful():
            raise SystemExit("desktop-qt unit tests failed")

    print(f"desktop-qt release checks passed for v{version}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
