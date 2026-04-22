use base64::{engine::general_purpose::STANDARD, Engine as _};
use minisign_verify::{PublicKey, Signature};
use serde::Deserialize;
use std::{
    collections::HashMap,
    env,
    fs,
    io::{self, ErrorKind},
    path::PathBuf,
};

type DynError = Box<dyn std::error::Error + Send + Sync>;

#[derive(Debug, Deserialize)]
struct TauriConfig {
    plugins: TauriPlugins,
}

#[derive(Debug, Deserialize)]
struct TauriPlugins {
    updater: TauriUpdaterConfig,
}

#[derive(Debug, Deserialize)]
struct TauriUpdaterConfig {
    pubkey: String,
}

#[derive(Debug, Deserialize)]
struct UpdaterManifest {
    version: String,
    platforms: HashMap<String, UpdaterManifestPlatform>,
}

#[derive(Debug, Deserialize)]
struct UpdaterManifestPlatform {
    signature: String,
    url: String,
}

#[derive(Debug)]
struct VerifyArgs {
    tauri_config: PathBuf,
    manifest: PathBuf,
    installer: PathBuf,
    signature: PathBuf,
    version: String,
    tag: String,
    repo: String,
}

fn main() {
    if let Err(error) = run() {
        eprintln!("ERROR: {error}");
        std::process::exit(1);
    }
}

fn run() -> Result<(), DynError> {
    let args = parse_args()?;
    let public_key = load_updater_public_key(&args.tauri_config)?;
    let signature_text = fs::read_to_string(&args.signature)?;
    let signature = Signature::decode(signature_text.trim())
        .map_err(|error| invalid_data(format!("failed to decode signature file: {error}")))?;
    let installer_bytes = fs::read(&args.installer)?;

    public_key
        .verify(&installer_bytes, &signature, true)
        .map_err(|error| invalid_data(format!("installer signature verification failed: {error}")))?;

    verify_manifest(&args, signature_text.trim())?;

    println!(
        "Verified updater bundle: {}",
        args.installer
            .file_name()
            .and_then(|name| name.to_str())
            .unwrap_or("installer")
    );
    Ok(())
}

fn parse_args() -> Result<VerifyArgs, DynError> {
    let mut tauri_config = None;
    let mut manifest = None;
    let mut installer = None;
    let mut signature = None;
    let mut version = None;
    let mut tag = None;
    let mut repo = None;

    let mut args = env::args().skip(1);
    while let Some(flag) = args.next() {
        match flag.as_str() {
            "--help" | "-h" => {
                print_usage();
                std::process::exit(0);
            }
            _ => {
                let value = args
                    .next()
                    .ok_or_else(|| invalid_input(format!("missing value for {flag}")))?;

                match flag.as_str() {
                    "--tauri-config" => tauri_config = Some(PathBuf::from(value)),
                    "--manifest" => manifest = Some(PathBuf::from(value)),
                    "--installer" => installer = Some(PathBuf::from(value)),
                    "--signature" => signature = Some(PathBuf::from(value)),
                    "--version" => version = Some(value),
                    "--tag" => tag = Some(value),
                    "--repo" => repo = Some(value),
                    _ => return Err(invalid_input(format!("unknown argument: {flag}")).into()),
                }
            }
        }
    }

    Ok(VerifyArgs {
        tauri_config: tauri_config.ok_or_else(|| invalid_input("missing --tauri-config"))?,
        manifest: manifest.ok_or_else(|| invalid_input("missing --manifest"))?,
        installer: installer.ok_or_else(|| invalid_input("missing --installer"))?,
        signature: signature.ok_or_else(|| invalid_input("missing --signature"))?,
        version: version.ok_or_else(|| invalid_input("missing --version"))?,
        tag: tag.ok_or_else(|| invalid_input("missing --tag"))?,
        repo: repo.ok_or_else(|| invalid_input("missing --repo"))?,
    })
}

fn print_usage() {
    eprintln!(
        "Usage: verify_updater_bundle --tauri-config <path> --manifest <path> --installer <path> --signature <path> --version <version> --tag <tag> --repo <owner/repo>"
    );
}

fn load_updater_public_key(path: &PathBuf) -> Result<PublicKey, DynError> {
    let raw = fs::read_to_string(path)?;
    let config = serde_json::from_str::<TauriConfig>(&raw)?;
    let decoded = STANDARD
        .decode(config.plugins.updater.pubkey.trim())
        .map_err(|error| invalid_data(format!("failed to decode updater pubkey: {error}")))?;
    let pubkey_text = String::from_utf8(decoded)
        .map_err(|error| invalid_data(format!("failed to decode updater pubkey text: {error}")))?;

    PublicKey::decode(pubkey_text.trim())
        .map_err(|error| invalid_data(format!("failed to parse updater pubkey: {error}")).into())
}

fn verify_manifest(args: &VerifyArgs, signature_text: &str) -> Result<(), DynError> {
    let raw = fs::read_to_string(&args.manifest)?;
    let manifest = serde_json::from_str::<UpdaterManifest>(&raw)?;
    if manifest.version != args.version {
        return Err(invalid_data(format!(
            "latest.json version mismatch: expected {}, got {}",
            args.version, manifest.version
        ))
        .into());
    }

    let platform = manifest
        .platforms
        .get("windows-x86_64")
        .ok_or_else(|| invalid_data("latest.json is missing platforms.windows-x86_64"))?;

    if platform.signature.trim() != signature_text {
        return Err(invalid_data("latest.json signature does not match the generated .sig file").into());
    }

    let installer_name = args
        .installer
        .file_name()
        .and_then(|name| name.to_str())
        .ok_or_else(|| invalid_data("unable to derive installer file name"))?;
    let expected_url = format!(
        "https://github.com/{}/releases/download/{}/{}",
        args.repo, args.tag, installer_name
    );

    if platform.url != expected_url {
        return Err(invalid_data(format!(
            "latest.json download url mismatch: expected {}, got {}",
            expected_url, platform.url
        ))
        .into());
    }

    Ok(())
}

fn invalid_input(message: impl Into<String>) -> io::Error {
    io::Error::new(ErrorKind::InvalidInput, message.into())
}

fn invalid_data(message: impl Into<String>) -> io::Error {
    io::Error::new(ErrorKind::InvalidData, message.into())
}
