from __future__ import annotations

import argparse
import base64
import hashlib
import json
from datetime import datetime, UTC
from pathlib import Path
from typing import Any

from nacl.signing import SigningKey, VerifyKey


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate or verify Qt desktop release manifests")
    subparsers = parser.add_subparsers(dest="command", required=True)

    generate = subparsers.add_parser("generate", help="Generate manifest and detached signature")
    generate.add_argument("--version", required=True)
    generate.add_argument("--installer", required=True, type=Path)
    generate.add_argument("--download-url", required=True)
    generate.add_argument("--output", required=True, type=Path)
    generate.add_argument("--signature-output", required=True, type=Path)
    generate.add_argument("--notes", default="")
    generate.add_argument("--private-key", default="")

    verify = subparsers.add_parser("verify", help="Verify manifest signature and installer hash")
    verify.add_argument("--manifest", required=True, type=Path)
    verify.add_argument("--signature", required=True, type=Path)
    verify.add_argument("--installer", required=True, type=Path)
    verify.add_argument("--public-key", required=True)
    verify.add_argument("--version", default="")
    verify.add_argument("--download-url", default="")

    keygen = subparsers.add_parser("keygen", help="Generate an Ed25519 signing keypair")
    keygen.add_argument("--output-dir", required=True, type=Path)

    return parser.parse_args()


def main() -> int:
    args = parse_args()
    if args.command == "generate":
        return generate_manifest(args)
    if args.command == "verify":
        return verify_manifest(args)
    return generate_keypair(args)


def generate_manifest(args: argparse.Namespace) -> int:
    private_key = (args.private_key or "").strip()
    if not private_key:
        raise SystemExit("--private-key is required for generate")

    installer_path = args.installer.resolve()
    if not installer_path.exists():
        raise SystemExit(f"installer not found: {installer_path}")

    sha256 = file_sha256(installer_path)
    size = installer_path.stat().st_size
    payload = {
        "version": args.version,
        "notes": args.notes,
        "pub_date": datetime.now(UTC).strftime("%Y-%m-%dT%H:%M:%SZ"),
        "platforms": {
            "windows-x86_64": {
                "url": args.download_url,
                "sha256": sha256,
                "size": size,
            }
        },
    }

    manifest_bytes = (json.dumps(payload, indent=2, ensure_ascii=False) + "\n").encode("utf-8")
    args.output.write_bytes(manifest_bytes)

    signing_key = SigningKey(base64.b64decode(private_key))
    signature = signing_key.sign(manifest_bytes).signature
    args.signature_output.write_text(base64.b64encode(signature).decode("ascii") + "\n", encoding="utf-8")

    print(f"Manifest: {args.output}")
    print(f"Signature: {args.signature_output}")
    print(f"SHA256: {sha256}")
    return 0


def verify_manifest(args: argparse.Namespace) -> int:
    manifest_bytes = args.manifest.read_bytes()
    signature_text = args.signature.read_text(encoding="utf-8").strip()
    verify_key = VerifyKey(base64.b64decode(args.public_key.strip()))
    verify_key.verify(manifest_bytes, base64.b64decode(signature_text))

    payload = json.loads(manifest_bytes.decode("utf-8"))
    platform = payload.get("platforms", {}).get("windows-x86_64")
    if not isinstance(platform, dict):
        raise SystemExit("manifest is missing platforms.windows-x86_64")

    if args.version and str(payload.get("version") or "") != args.version:
        raise SystemExit(
            f"manifest version mismatch: expected {args.version}, got {payload.get('version')}"
        )

    if args.download_url and str(platform.get("url") or "") != args.download_url:
        raise SystemExit(
            f"manifest url mismatch: expected {args.download_url}, got {platform.get('url')}"
        )

    actual_sha256 = file_sha256(args.installer)
    if str(platform.get("sha256") or "").lower() != actual_sha256:
        raise SystemExit("manifest sha256 does not match installer")

    actual_size = args.installer.stat().st_size
    if int(platform.get("size") or 0) != actual_size:
        raise SystemExit("manifest size does not match installer")

    print(f"Verified manifest: {args.manifest}")
    return 0


def generate_keypair(args: argparse.Namespace) -> int:
    args.output_dir.mkdir(parents=True, exist_ok=True)
    signing_key = SigningKey.generate()
    verify_key = signing_key.verify_key

    private_key = base64.b64encode(bytes(signing_key)).decode("ascii")
    public_key = base64.b64encode(bytes(verify_key)).decode("ascii")

    (args.output_dir / "qt-update-private.key").write_text(private_key + "\n", encoding="utf-8")
    (args.output_dir / "qt-update-public.key").write_text(public_key + "\n", encoding="utf-8")
    print(f"Private key: {args.output_dir / 'qt-update-private.key'}")
    print(f"Public key: {args.output_dir / 'qt-update-public.key'}")
    return 0


def file_sha256(path: Path) -> str:
    digest = hashlib.sha256()
    with path.open("rb") as handle:
        while True:
            chunk = handle.read(1024 * 256)
            if not chunk:
                break
            digest.update(chunk)
    return digest.hexdigest().lower()


if __name__ == "__main__":
    raise SystemExit(main())
