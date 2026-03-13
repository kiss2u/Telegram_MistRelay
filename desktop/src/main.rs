#![cfg_attr(not(debug_assertions), windows_subsystem = "windows")]

use std::{
    collections::HashMap,
    fs,
    io::{self, BufRead, BufReader, ErrorKind, Read, Seek, SeekFrom, Write},
    net::{TcpListener, TcpStream},
    path::{Component, Path, PathBuf},
    sync::{
        atomic::{AtomicBool, AtomicU64, Ordering},
        Arc, Condvar, Mutex,
    },
    thread,
    time::Duration,
};
use reqwest::{blocking::Client, header, Proxy, StatusCode};
use serde::{Deserialize, Serialize};
use tauri_plugin_dialog::{DialogExt, FilePath};
use url::Url;

const PREVIEW_READY_BYTES: u64 = 4 * 1024 * 1024;

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
struct DesktopProxyConfig {
    enabled: bool,
    url: String,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
struct DesktopDownloadConfig {
    download_dir: String,
    max_concurrent_downloads: u32,
    threads_per_download: u32,
}

impl Default for DesktopDownloadConfig {
    fn default() -> Self {
        Self {
            download_dir: String::new(),
            max_concurrent_downloads: 3,
            threads_per_download: 4,
        }
    }
}

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
#[serde(default, rename_all = "camelCase")]
struct DesktopClientConfig {
    proxy: DesktopProxyConfig,
    download: DesktopDownloadConfig,
}

struct ConcurrencyLimiter {
    active: Mutex<usize>,
    max: Mutex<usize>,
    condvar: Condvar,
}

impl ConcurrencyLimiter {
    fn new(max: usize) -> Self {
        Self {
            active: Mutex::new(0),
            max: Mutex::new(max.max(1)),
            condvar: Condvar::new(),
        }
    }

    fn acquire(&self) {
        let mut active = self.active.lock().unwrap();
        loop {
            let max = *self.max.lock().unwrap();
            if *active < max {
                *active += 1;
                return;
            }
            active = self.condvar.wait(active).unwrap();
        }
    }

    fn release(&self) {
        let mut active = self.active.lock().unwrap();
        *active = active.saturating_sub(1);
        self.condvar.notify_one();
    }

    fn update_max(&self, new_max: usize) {
        *self.max.lock().unwrap() = new_max.max(1);
        self.condvar.notify_all();
    }
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopTransferResult {
    file_name: String,
    local_path: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopDownloadSession {
    transfer_id: String,
    file_name: String,
    local_path: String,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopPreviewSession {
    transfer_id: String,
    stream_url: String,
    local_path: String,
    ready_for_preview: bool,
}

#[derive(Debug, Clone, Serialize)]
#[serde(rename_all = "camelCase")]
struct DesktopTransferStatus {
    transfer_id: String,
    file_name: String,
    local_path: String,
    downloaded_bytes: u64,
    total_bytes: Option<u64>,
    progress_percent: f64,
    state: String,
    ready_for_preview: bool,
    error: Option<String>,
}

#[derive(Debug, Default)]
struct TransferProgress {
    downloaded_bytes: u64,
    total_bytes: Option<u64>,
    complete: bool,
    ready_for_preview: bool,
    error: Option<String>,
}

#[derive(Clone, Copy)]
enum TransferKind {
    Download,
    Preview,
}

struct TransferHandle {
    file_name: String,
    source_url: String,
    local_path: PathBuf,
    complete_marker_path: Option<PathBuf>,
    kind: TransferKind,
    inner: Arc<(Mutex<TransferProgress>, Condvar)>,
    worker_started: AtomicBool,
}

impl TransferHandle {
    fn new_download(file_name: String, source_url: String, local_path: PathBuf) -> Self {
        Self {
            file_name,
            source_url,
            local_path,
            complete_marker_path: None,
            kind: TransferKind::Download,
            inner: Arc::new((Mutex::new(TransferProgress::default()), Condvar::new())),
            worker_started: AtomicBool::new(false),
        }
    }

    fn new_preview(file_name: String, source_url: String, local_path: PathBuf) -> Self {
        Self {
            file_name,
            source_url,
            complete_marker_path: Some(PathBuf::from(format!("{}.complete", local_path.display()))),
            local_path,
            kind: TransferKind::Preview,
            inner: Arc::new((Mutex::new(TransferProgress::default()), Condvar::new())),
            worker_started: AtomicBool::new(false),
        }
    }
}

struct DesktopRuntimeState {
    preview_server_port: u16,
    preview_transfers: Arc<Mutex<HashMap<String, Arc<TransferHandle>>>>,
    preview_sessions: Arc<Mutex<HashMap<String, Arc<TransferHandle>>>>,
    download_transfers: Arc<Mutex<HashMap<String, Arc<TransferHandle>>>>,
    download_sessions: Arc<Mutex<HashMap<String, Arc<TransferHandle>>>>,
    next_transfer_id: AtomicU64,
    download_limiter: Arc<ConcurrencyLimiter>,
    threads_per_download: Arc<Mutex<u32>>,
}

impl DesktopRuntimeState {
    fn new() -> Result<Self, String> {
        let preview_transfers = Arc::new(Mutex::new(HashMap::new()));
        let preview_sessions = Arc::new(Mutex::new(HashMap::new()));
        let download_transfers = Arc::new(Mutex::new(HashMap::new()));
        let download_sessions = Arc::new(Mutex::new(HashMap::new()));
        let listener = TcpListener::bind("127.0.0.1:0")
            .map_err(|error| format!("启动本地预览服务失败: {error}"))?;
        let port = listener
            .local_addr()
            .map_err(|error| format!("获取本地预览端口失败: {error}"))?
            .port();

        spawn_preview_server(listener, Arc::clone(&preview_sessions));

        let config = load_desktop_client_config().unwrap_or_default();

        Ok(Self {
            preview_server_port: port,
            preview_transfers,
            preview_sessions,
            download_transfers,
            download_sessions,
            next_transfer_id: AtomicU64::new(1),
            download_limiter: Arc::new(ConcurrencyLimiter::new(
                config.download.max_concurrent_downloads as usize,
            )),
            threads_per_download: Arc::new(Mutex::new(config.download.threads_per_download)),
        })
    }
}

fn desktop_client_config_path() -> Result<PathBuf, String> {
    let config_dir =
        dirs::config_dir().ok_or_else(|| "无法定位桌面客户端配置目录".to_string())?;

    Ok(config_dir.join("MistRelay").join("desktop-client.json"))
}

fn load_desktop_client_config() -> Result<DesktopClientConfig, String> {
    let path = desktop_client_config_path()?;
    let raw = match fs::read_to_string(&path) {
        Ok(raw) => raw,
        Err(error) if error.kind() == ErrorKind::NotFound => {
            return Ok(DesktopClientConfig::default());
        }
        Err(error) => {
            return Err(format!("读取桌面客户端配置失败: {error}"));
        }
    };

    serde_json::from_str(&raw).map_err(|error| format!("解析桌面客户端配置失败: {error}"))
}

fn validate_proxy_url(raw: &str) -> Result<Url, String> {
    let parsed = Url::parse(raw).map_err(|error| format!("代理地址格式不正确: {error}"))?;

    match parsed.scheme() {
        "http" | "socks5" => Ok(parsed),
        _ => Err("代理地址只支持 http:// 或 socks5://".to_string()),
    }
}

fn normalized_proxy_url(config: &DesktopClientConfig) -> Result<Option<Url>, String> {
    if !config.proxy.enabled {
        return Ok(None);
    }

    let proxy_url = config.proxy.url.trim();
    if proxy_url.is_empty() {
        return Err("已启用桌面代理，但代理地址为空".to_string());
    }

    validate_proxy_url(proxy_url).map(Some)
}

fn apply_process_proxy_env(config: &DesktopClientConfig) -> Result<(), String> {
    const PROXY_ENV_KEYS: [&str; 6] = [
        "HTTP_PROXY",
        "HTTPS_PROXY",
        "ALL_PROXY",
        "http_proxy",
        "https_proxy",
        "all_proxy",
    ];

    if let Some(proxy_url) = normalized_proxy_url(config)? {
        let proxy = proxy_url.to_string();
        for key in PROXY_ENV_KEYS {
            std::env::set_var(key, &proxy);
        }
    } else {
        for key in PROXY_ENV_KEYS {
            std::env::remove_var(key);
        }
    }

    Ok(())
}

fn save_desktop_client_config_file(config: &DesktopClientConfig) -> Result<(), String> {
    let path = desktop_client_config_path()?;
    let Some(parent) = path.parent() else {
        return Err("桌面客户端配置目录不可用".to_string());
    };

    fs::create_dir_all(parent).map_err(|error| format!("创建桌面客户端配置目录失败: {error}"))?;

    let serialized = serde_json::to_string_pretty(config)
        .map_err(|error| format!("序列化桌面客户端配置失败: {error}"))?;

    fs::write(path, serialized).map_err(|error| format!("保存桌面客户端配置失败: {error}"))
}

fn build_http_client() -> Result<Client, String> {
    let mut builder = Client::builder()
        .connect_timeout(Duration::from_secs(15))
        .timeout(Duration::from_secs(60 * 60))
        .user_agent("MistRelay Desktop");

    if let Some(proxy_url) = normalized_proxy_url(&load_desktop_client_config()?)? {
        let proxy = Proxy::all(proxy_url.as_str())
            .map_err(|error| format!("创建桌面代理失败: {error}"))?;
        builder = builder.proxy(proxy);
    }

    builder
        .build()
        .map_err(|error| format!("创建桌面网络客户端失败: {error}"))
}

fn sanitize_path_component(value: &str) -> String {
    let sanitized = value
        .chars()
        .map(|character| match character {
            '<' | '>' | ':' | '"' | '/' | '\\' | '|' | '?' | '*' => '_',
            c if c.is_control() => '_',
            c => c,
        })
        .collect::<String>()
        .trim()
        .trim_matches('.')
        .to_string();

    if sanitized.is_empty() {
        "_".to_string()
    } else {
        sanitized
    }
}

fn build_relative_file_path(remote: &str, remote_path: &str, file_name: &str) -> PathBuf {
    let mut relative = PathBuf::new();
    relative.push(sanitize_path_component(remote));

    for component in Path::new(remote_path).components() {
        if let Component::Normal(part) = component {
            relative.push(sanitize_path_component(&part.to_string_lossy()));
        }
    }

    if relative.file_name().is_none() {
        relative.push(sanitize_path_component(file_name));
    }

    relative
}

fn default_downloads_root_dir() -> Result<PathBuf, String> {
    let download_dir =
        dirs::download_dir().ok_or_else(|| "无法定位系统下载目录".to_string())?;
    Ok(download_dir.join("MistRelay"))
}

fn normalized_download_dir(raw: &str) -> Result<String, String> {
    let trimmed = raw.trim();
    if trimmed.is_empty() {
        return Ok(String::new());
    }

    let path = PathBuf::from(trimmed);
    if !path.is_absolute() {
        return Err("下载目录必须是绝对路径".to_string());
    }

    fs::create_dir_all(&path).map_err(|error| format!("创建下载目录失败: {error}"))?;
    let metadata = fs::metadata(&path).map_err(|error| format!("读取下载目录失败: {error}"))?;
    if !metadata.is_dir() {
        return Err("下载目录必须是文件夹".to_string());
    }

    Ok(path.to_string_lossy().to_string())
}

fn downloads_root_dir() -> Result<PathBuf, String> {
    let config = load_desktop_client_config()?;
    if config.download.download_dir.trim().is_empty() {
        return default_downloads_root_dir();
    }

    Ok(PathBuf::from(&config.download.download_dir))
}

fn preview_cache_root_dir() -> Result<PathBuf, String> {
    let cache_dir = dirs::cache_dir().ok_or_else(|| "无法定位桌面缓存目录".to_string())?;
    Ok(cache_dir.join("MistRelay").join("preview-cache"))
}

fn ensure_parent_dir(path: &Path) -> Result<(), String> {
    let Some(parent) = path.parent() else {
        return Err("目标目录不可用".to_string());
    };

    fs::create_dir_all(parent).map_err(|error| format!("创建目标目录失败: {error}"))
}

fn download_to_path(source_url: &str, destination: &Path) -> Result<(), String> {
    ensure_parent_dir(destination)?;

    let client = build_http_client()?;
    let mut response = client
        .get(source_url)
        .send()
        .map_err(|error| format!("下载文件失败: {error}"))?;

    if response.status() != StatusCode::OK && response.status() != StatusCode::PARTIAL_CONTENT {
        return Err(format!("下载文件失败: 服务返回 {}", response.status()));
    }

    let temp_path = destination.with_extension("download");
    let mut temp_file =
        fs::File::create(&temp_path).map_err(|error| format!("创建临时文件失败: {error}"))?;

    io::copy(&mut response, &mut temp_file).map_err(|error| format!("写入本地文件失败: {error}"))?;

    if destination.exists() {
        fs::remove_file(destination).map_err(|error| format!("覆盖旧文件失败: {error}"))?;
    }

    fs::rename(&temp_path, destination).map_err(|error| format!("保存文件失败: {error}"))?;
    Ok(())
}

fn preview_ready_threshold(total_bytes: Option<u64>) -> u64 {
    match total_bytes {
        Some(total) => total.min(PREVIEW_READY_BYTES).max(512 * 1024),
        None => PREVIEW_READY_BYTES,
    }
}

fn mark_transfer_failed(handle: &TransferHandle, message: String) {
    let (lock, condvar) = &*handle.inner;
    if let Ok(mut progress) = lock.lock() {
        progress.error = Some(message);
        condvar.notify_all();
    }
}

fn spawn_transfer(
    handle: Arc<TransferHandle>,
    limiter: Option<Arc<ConcurrencyLimiter>>,
    threads: u32,
) {
    if handle.worker_started.swap(true, Ordering::SeqCst) {
        return;
    }

    thread::spawn(move || {
        if let Some(ref limiter) = limiter {
            limiter.acquire();
        }

        let result = match handle.kind {
            TransferKind::Download if threads > 1 => {
                multi_thread_download(&handle, threads)
            }
            _ => stream_transfer_to_path(&handle),
        };

        if let Err(error) = result {
            mark_transfer_failed(&handle, error);
        }

        if let Some(limiter) = limiter {
            limiter.release();
        }
    });
}

fn stream_transfer_to_path(handle: &TransferHandle) -> Result<(), String> {
    ensure_parent_dir(&handle.local_path)?;

    if let Some(complete_marker_path) = &handle.complete_marker_path {
        if complete_marker_path.exists() && handle.local_path.exists() {
            let size = fs::metadata(&handle.local_path)
                .map_err(|error| format!("读取本地预览缓存失败: {error}"))?
                .len();
            let (lock, condvar) = &*handle.inner;
            let mut progress = lock.lock().map_err(|_| "缓存状态已损坏".to_string())?;
            progress.downloaded_bytes = size;
            progress.total_bytes = Some(size);
            progress.complete = true;
            progress.ready_for_preview = true;
            condvar.notify_all();
            return Ok(());
        }
    }

    if handle.local_path.exists() {
        let _ = fs::remove_file(&handle.local_path);
    }
    if let Some(complete_marker_path) = &handle.complete_marker_path {
        if complete_marker_path.exists() {
            let _ = fs::remove_file(complete_marker_path);
        }
    }

    let client = build_http_client()?;
    let mut response = client
        .get(&handle.source_url)
        .send()
        .map_err(|error| format!("创建本地流缓存失败: {error}"))?;

    if response.status() != StatusCode::OK && response.status() != StatusCode::PARTIAL_CONTENT {
        return Err(format!("本地流缓存失败: 服务返回 {}", response.status()));
    }

    let total_bytes = response.content_length();
    {
        let (lock, condvar) = &*handle.inner;
        let mut progress = lock.lock().map_err(|_| "缓存状态已损坏".to_string())?;
        progress.total_bytes = total_bytes;
        progress.ready_for_preview = false;
        condvar.notify_all();
    }

    let mut file = fs::File::create(&handle.local_path)
        .map_err(|error| format!("创建本地预览缓存文件失败: {error}"))?;
    let mut buffer = [0_u8; 64 * 1024];

    loop {
        let read = response
            .read(&mut buffer)
            .map_err(|error| format!("读取视频流失败: {error}"))?;
        if read == 0 {
            break;
        }

        file.write_all(&buffer[..read])
            .map_err(|error| format!("写入本地预览缓存失败: {error}"))?;
        file.flush()
            .map_err(|error| format!("刷新本地预览缓存失败: {error}"))?;

        let (lock, condvar) = &*handle.inner;
        let mut progress = lock.lock().map_err(|_| "缓存状态已损坏".to_string())?;
        progress.downloaded_bytes += read as u64;
        progress.ready_for_preview = matches!(handle.kind, TransferKind::Preview)
            && (progress.complete || progress.downloaded_bytes >= preview_ready_threshold(progress.total_bytes));
        condvar.notify_all();
    }

    if let Some(complete_marker_path) = &handle.complete_marker_path {
        fs::write(complete_marker_path, b"ok")
            .map_err(|error| format!("写入预览完成标记失败: {error}"))?;
    }

    let final_size = fs::metadata(&handle.local_path)
        .map_err(|error| format!("读取本地预览缓存大小失败: {error}"))?
        .len();

    let (lock, condvar) = &*handle.inner;
    let mut progress = lock.lock().map_err(|_| "缓存状态已损坏".to_string())?;
    progress.downloaded_bytes = final_size;
    if progress.total_bytes.is_none() {
        progress.total_bytes = Some(final_size);
    }
    progress.complete = true;
    progress.ready_for_preview = matches!(handle.kind, TransferKind::Preview);
    condvar.notify_all();

    Ok(())
}

fn multi_thread_download(handle: &TransferHandle, num_threads: u32) -> Result<(), String> {
    ensure_parent_dir(&handle.local_path)?;

    let client = build_http_client()?;
    let head_resp = client
        .head(&handle.source_url)
        .send()
        .map_err(|e| format!("HEAD 请求失败: {e}"))?;

    let accepts_ranges = head_resp
        .headers()
        .get(header::ACCEPT_RANGES)
        .and_then(|v| v.to_str().ok())
        .map(|v| v.eq_ignore_ascii_case("bytes"))
        .unwrap_or(false);
    let total_size = head_resp.content_length();

    if !accepts_ranges || total_size.is_none() || num_threads <= 1 {
        return stream_transfer_to_path(handle);
    }

    let total = total_size.unwrap();
    if total == 0 {
        return stream_transfer_to_path(handle);
    }

    {
        let (lock, condvar) = &*handle.inner;
        let mut progress = lock.lock().map_err(|_| "状态已损坏".to_string())?;
        progress.total_bytes = Some(total);
        condvar.notify_all();
    }

    let file = fs::File::create(&handle.local_path)
        .map_err(|e| format!("创建文件失败: {e}"))?;
    file.set_len(total)
        .map_err(|e| format!("预分配文件空间失败: {e}"))?;
    drop(file);

    let chunk_size = total / num_threads as u64;
    let shared_downloaded = Arc::new(AtomicU64::new(0));
    let shared_error: Arc<Mutex<Option<String>>> = Arc::new(Mutex::new(None));

    let mut thread_handles = Vec::with_capacity(num_threads as usize);

    for i in 0..num_threads {
        let start = i as u64 * chunk_size;
        let end = if i == num_threads - 1 {
            total - 1
        } else {
            (i + 1) as u64 * chunk_size - 1
        };

        let url = handle.source_url.clone();
        let path = handle.local_path.clone();
        let downloaded = Arc::clone(&shared_downloaded);
        let error = Arc::clone(&shared_error);
        let progress_inner = Arc::clone(&handle.inner);

        thread_handles.push(thread::spawn(move || {
            if let Err(e) = download_chunk(&url, &path, start, end, &downloaded, &progress_inner) {
                let mut err_lock = error.lock().unwrap();
                if err_lock.is_none() {
                    *err_lock = Some(e);
                }
            }
        }));
    }

    for th in thread_handles {
        let _ = th.join();
    }

    if let Some(error) = shared_error.lock().unwrap().take() {
        let _ = fs::remove_file(&handle.local_path);
        return Err(error);
    }

    let (lock, condvar) = &*handle.inner;
    let mut progress = lock.lock().map_err(|_| "状态已损坏".to_string())?;
    progress.downloaded_bytes = total;
    progress.total_bytes = Some(total);
    progress.complete = true;
    condvar.notify_all();

    Ok(())
}

fn download_chunk(
    url: &str,
    path: &Path,
    start: u64,
    end: u64,
    shared_downloaded: &AtomicU64,
    progress_inner: &Arc<(Mutex<TransferProgress>, Condvar)>,
) -> Result<(), String> {
    let client = build_http_client()?;
    let range = format!("bytes={}-{}", start, end);

    let mut response = client
        .get(url)
        .header(header::RANGE, &range)
        .send()
        .map_err(|e| format!("分片下载失败: {e}"))?;

    let status = response.status();
    if status != StatusCode::PARTIAL_CONTENT && status != StatusCode::OK {
        return Err(format!("分片下载失败: 服务返回 {status}"));
    }

    let mut file = fs::OpenOptions::new()
        .write(true)
        .open(path)
        .map_err(|e| format!("打开文件失败: {e}"))?;
    file.seek(SeekFrom::Start(start))
        .map_err(|e| format!("定位文件失败: {e}"))?;

    let mut buffer = [0_u8; 64 * 1024];
    loop {
        let read = response
            .read(&mut buffer)
            .map_err(|e| format!("读取分片数据失败: {e}"))?;
        if read == 0 {
            break;
        }

        file.write_all(&buffer[..read])
            .map_err(|e| format!("写入分片数据失败: {e}"))?;

        let total_downloaded =
            shared_downloaded.fetch_add(read as u64, Ordering::Relaxed) + read as u64;

        let (lock, condvar) = &**progress_inner;
        if let Ok(mut progress) = lock.lock() {
            progress.downloaded_bytes = total_downloaded;
            condvar.notify_all();
        }
    }

    Ok(())
}

fn spawn_progress_emitter(
    app: tauri::AppHandle,
    transfer_id: String,
    handle: Arc<TransferHandle>,
) {
    thread::spawn(move || {
        loop {
            let status = match snapshot_transfer_status(&transfer_id, &handle) {
                Ok(s) => s,
                Err(_) => break,
            };

            let is_terminal = status.state == "completed" || status.state == "error";
            let _ = app.emit("desktop-transfer-progress", &status);

            if is_terminal {
                break;
            }

            thread::sleep(Duration::from_millis(250));
        }
    });
}

fn snapshot_transfer_status(transfer_id: &str, handle: &TransferHandle) -> Result<DesktopTransferStatus, String> {
    let (lock, _) = &*handle.inner;
    let progress = lock.lock().map_err(|_| "缓存状态已损坏".to_string())?;

    let progress_percent = progress.total_bytes.map_or(0.0, |total| {
        if total == 0 {
            0.0
        } else {
            ((progress.downloaded_bytes as f64 / total as f64) * 100.0).min(100.0)
        }
    });

    let state = if progress.error.is_some() {
        "error"
    } else if progress.complete {
        "completed"
    } else if progress.ready_for_preview {
        "ready"
    } else if progress.downloaded_bytes > 0 {
        "downloading"
    } else {
        "pending"
    };

    Ok(DesktopTransferStatus {
        transfer_id: transfer_id.to_string(),
        file_name: handle.file_name.clone(),
        local_path: handle.local_path.to_string_lossy().to_string(),
        downloaded_bytes: progress.downloaded_bytes,
        total_bytes: progress.total_bytes,
        progress_percent,
        state: state.to_string(),
        ready_for_preview: progress.ready_for_preview,
        error: progress.error.clone(),
    })
}

fn wait_for_available_bytes(handle: &TransferHandle, needed_bytes: u64) -> Result<TransferProgress, String> {
    let (lock, condvar) = &*handle.inner;
    let mut progress = lock.lock().map_err(|_| "缓存状态已损坏".to_string())?;

    loop {
        if let Some(error) = &progress.error {
            return Err(error.clone());
        }

        if progress.complete || progress.downloaded_bytes >= needed_bytes {
            return Ok(TransferProgress {
                downloaded_bytes: progress.downloaded_bytes,
                total_bytes: progress.total_bytes,
                complete: progress.complete,
                ready_for_preview: progress.ready_for_preview,
                error: progress.error.clone(),
            });
        }

        progress = condvar
            .wait(progress)
            .map_err(|_| "等待本地缓存失败".to_string())?;
    }
}

fn parse_range_header(value: &str) -> Option<(u64, Option<u64>)> {
    let trimmed = value.trim();
    let bytes = trimmed.strip_prefix("bytes=")?;
    let (start, end) = bytes.split_once('-')?;
    let start = start.parse::<u64>().ok()?;
    let end = if end.trim().is_empty() {
        None
    } else {
        Some(end.parse::<u64>().ok()?)
    };

    Some((start, end))
}

fn send_http_headers(
    stream: &mut TcpStream,
    status_line: &str,
    content_type: &str,
    content_length: u64,
    content_range: Option<String>,
) -> Result<(), String> {
    let mut response = format!(
        "HTTP/1.1 {status_line}\r\nContent-Type: {content_type}\r\nAccept-Ranges: bytes\r\nContent-Length: {content_length}\r\nConnection: close\r\n"
    );

    if let Some(content_range) = content_range {
        response.push_str(&format!("Content-Range: {content_range}\r\n"));
    }

    response.push_str("\r\n");
    stream
        .write_all(response.as_bytes())
        .map_err(|error| format!("写入本地流响应头失败: {error}"))
}

fn send_simple_response(stream: &mut TcpStream, status_line: &str, body: &str) -> Result<(), String> {
    let response = format!(
        "HTTP/1.1 {status_line}\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Length: {}\r\nConnection: close\r\n\r\n{}",
        body.as_bytes().len(),
        body
    );
    stream
        .write_all(response.as_bytes())
        .map_err(|error| format!("写入本地流响应失败: {error}"))
}

fn stream_file_body(
    stream: &mut TcpStream,
    handle: &TransferHandle,
    start: u64,
    end: u64,
) -> Result<(), String> {
    let mut file = fs::File::open(&handle.local_path)
        .map_err(|error| format!("打开本地缓存文件失败: {error}"))?;
    file.seek(SeekFrom::Start(start))
        .map_err(|error| format!("定位本地缓存文件失败: {error}"))?;

    let mut position = start;
    let mut buffer = [0_u8; 64 * 1024];

    while position <= end {
        let snapshot = wait_for_available_bytes(handle, position + 1)?;
        let available_end = if snapshot.complete {
            snapshot
                .total_bytes
                .unwrap_or(snapshot.downloaded_bytes)
                .saturating_sub(1)
        } else {
            snapshot.downloaded_bytes.saturating_sub(1)
        };

        if available_end < position {
            continue;
        }

        let chunk_end = available_end.min(end);
        let mut remaining = chunk_end - position + 1;

        while remaining > 0 {
            let read_len = remaining.min(buffer.len() as u64) as usize;
            let bytes_read = file
                .read(&mut buffer[..read_len])
                .map_err(|error| format!("读取本地缓存文件失败: {error}"))?;

            if bytes_read == 0 {
                thread::sleep(Duration::from_millis(50));
                file.seek(SeekFrom::Start(position))
                    .map_err(|error| format!("重新定位本地缓存文件失败: {error}"))?;
                continue;
            }

            stream
                .write_all(&buffer[..bytes_read])
                .map_err(|error| format!("写入本地视频流失败: {error}"))?;
            position += bytes_read as u64;
            remaining = remaining.saturating_sub(bytes_read as u64);
        }
    }

    Ok(())
}

fn handle_preview_connection(
    mut stream: TcpStream,
    preview_sessions: &Arc<Mutex<HashMap<String, Arc<TransferHandle>>>>,
) -> Result<(), String> {
    let mut reader = BufReader::new(
        stream
            .try_clone()
            .map_err(|error| format!("复制本地预览连接失败: {error}"))?,
    );

    let mut request_line = String::new();
    reader
        .read_line(&mut request_line)
        .map_err(|error| format!("读取本地预览请求失败: {error}"))?;

    if request_line.trim().is_empty() {
        return Ok(());
    }

    let mut parts = request_line.split_whitespace();
    let method = parts.next().unwrap_or_default().to_uppercase();
    let path = parts.next().unwrap_or_default();

    let mut range_header = None;
    loop {
        let mut header_line = String::new();
        reader
            .read_line(&mut header_line)
            .map_err(|error| format!("读取本地预览请求头失败: {error}"))?;
        if header_line == "\r\n" || header_line.is_empty() {
            break;
        }
        if let Some((name, value)) = header_line.split_once(':') {
            if name.eq_ignore_ascii_case("Range") {
                range_header = Some(value.trim().to_string());
            }
        }
    }

    if method != "GET" && method != "HEAD" {
        return send_simple_response(&mut stream, "405 Method Not Allowed", "method not allowed");
    }

    let Some(transfer_id) = path.strip_prefix("/preview/") else {
        return send_simple_response(&mut stream, "404 Not Found", "not found");
    };

    let handle = {
        let sessions = preview_sessions
            .lock()
            .map_err(|_| "本地预览会话已损坏".to_string())?;
        sessions.get(transfer_id).cloned()
    };

    let Some(handle) = handle else {
        return send_simple_response(&mut stream, "404 Not Found", "preview session not found");
    };

    let snapshot = wait_for_available_bytes(&handle, 1)?;
    let total_bytes = match snapshot.total_bytes {
        Some(total) => total,
        None if snapshot.complete => snapshot.downloaded_bytes,
        None => {
            let final_snapshot = wait_for_available_bytes(&handle, preview_ready_threshold(None))?;
            final_snapshot
                .total_bytes
                .unwrap_or(final_snapshot.downloaded_bytes)
        }
    };

    if total_bytes == 0 {
        return send_simple_response(&mut stream, "404 Not Found", "empty preview");
    }

    let mime = mime_guess::from_path(&handle.local_path)
        .first_or_octet_stream()
        .to_string();

    let range = range_header
        .as_deref()
        .and_then(parse_range_header)
        .unwrap_or((0, None));
    let (start, requested_end) = range;

    if start >= total_bytes {
        return send_simple_response(
            &mut stream,
            "416 Range Not Satisfiable",
            "range not satisfiable",
        );
    }

    let end = requested_end.unwrap_or(total_bytes.saturating_sub(1)).min(total_bytes - 1);
    let content_length = end - start + 1;
    let is_partial = range_header.is_some();
    let status_line = if is_partial {
        "206 Partial Content"
    } else {
        "200 OK"
    };
    let content_range = if is_partial {
        Some(format!("bytes {start}-{end}/{total_bytes}"))
    } else {
        None
    };

    send_http_headers(&mut stream, status_line, &mime, content_length, content_range)?;

    if method == "HEAD" {
        return Ok(());
    }

    stream_file_body(&mut stream, &handle, start, end)
}

fn spawn_preview_server(
    listener: TcpListener,
    preview_sessions: Arc<Mutex<HashMap<String, Arc<TransferHandle>>>>,
) {
    thread::spawn(move || {
        for connection in listener.incoming() {
            let Ok(stream) = connection else {
                continue;
            };
            let sessions = Arc::clone(&preview_sessions);
            thread::spawn(move || {
                let _ = handle_preview_connection(stream, &sessions);
            });
        }
    });
}

fn apply_saved_proxy<R: tauri::Runtime>(context: &mut tauri::Context<R>) -> Result<(), String> {
    let config = load_desktop_client_config()?;
    let Some(proxy_url) = normalized_proxy_url(&config)? else {
        return Ok(());
    };

    let windows = &mut context.config_mut().app.windows;
    let idx = windows
        .iter()
        .position(|window| window.label == "main")
        .or_else(|| if windows.is_empty() { None } else { Some(0) })
        .ok_or_else(|| "未找到桌面主窗口配置".to_string())?;

    windows[idx].proxy_url = Some(proxy_url);

    Ok(())
}

#[tauri::command]
fn get_desktop_client_config() -> Result<DesktopClientConfig, String> {
    load_desktop_client_config()
}

#[tauri::command]
fn get_default_desktop_download_dir() -> Result<String, String> {
    Ok(default_downloads_root_dir()?.to_string_lossy().to_string())
}

fn dialog_file_path_to_string(path: FilePath) -> Option<String> {
    match path {
        FilePath::Path(path) => Some(path.to_string_lossy().to_string()),
        _ => None,
    }
}

#[tauri::command]
async fn pick_desktop_download_dir(
    app: tauri::AppHandle,
    current_dir: Option<String>,
) -> Result<Option<String>, String> {
    let mut dialog = app.dialog().file();

    let initial_dir = current_dir
        .as_deref()
        .map(str::trim)
        .filter(|value| !value.is_empty())
        .map(PathBuf::from)
        .filter(|path| path.exists() && path.is_dir())
        .or_else(|| default_downloads_root_dir().ok());

    if let Some(initial_dir) = initial_dir {
        dialog = dialog.set_directory(initial_dir);
    }

    Ok(dialog.blocking_pick_folder().and_then(dialog_file_path_to_string))
}

#[tauri::command]
fn save_desktop_client_config(
    state: tauri::State<'_, DesktopRuntimeState>,
    config: DesktopClientConfig,
) -> Result<(), String> {
    let proxy_url = config.proxy.url.trim().to_string();
    let download_dir = normalized_download_dir(&config.download.download_dir)?;
    let normalized_config = DesktopClientConfig {
        proxy: DesktopProxyConfig {
            enabled: config.proxy.enabled,
            url: proxy_url,
        },
        download: DesktopDownloadConfig {
            download_dir,
            max_concurrent_downloads: config.download.max_concurrent_downloads.max(1),
            threads_per_download: config.download.threads_per_download.clamp(1, 32),
        },
    };

    let _ = normalized_proxy_url(&normalized_config)?;
    save_desktop_client_config_file(&normalized_config)?;
    apply_process_proxy_env(&normalized_config)?;

    state
        .download_limiter
        .update_max(normalized_config.download.max_concurrent_downloads as usize);
    if let Ok(mut threads) = state.threads_per_download.lock() {
        *threads = normalized_config.download.threads_per_download;
    }

    Ok(())
}

#[tauri::command]
fn restart_desktop_app(app: tauri::AppHandle) {
    app.request_restart();
}

#[tauri::command]
fn desktop_start_download(
    app: tauri::AppHandle,
    state: tauri::State<'_, DesktopRuntimeState>,
    source_url: String,
    remote: String,
    remote_path: String,
    file_name: String,
) -> Result<DesktopDownloadSession, String> {
    let relative_path = build_relative_file_path(&remote, &remote_path, &file_name);
    let destination = downloads_root_dir()?.join(relative_path);
    let transfer_key = destination.to_string_lossy().to_string();

    let handle = {
        let mut transfers = state
            .download_transfers
            .lock()
            .map_err(|_| "本地下载状态已损坏".to_string())?;

        if let Some(existing) = transfers.get(&transfer_key) {
            Arc::clone(existing)
        } else {
            let handle = Arc::new(TransferHandle::new_download(
                file_name.clone(),
                source_url,
                destination.clone(),
            ));
            transfers.insert(transfer_key, Arc::clone(&handle));
            handle
        }
    };

    let threads = *state
        .threads_per_download
        .lock()
        .map_err(|_| "读取线程配置失败".to_string())?;

    spawn_transfer(
        Arc::clone(&handle),
        Some(Arc::clone(&state.download_limiter)),
        threads,
    );

    let transfer_id = format!(
        "{}-{}",
        std::process::id(),
        state.next_transfer_id.fetch_add(1, Ordering::SeqCst)
    );

    {
        let mut sessions = state
            .download_sessions
            .lock()
            .map_err(|_| "本地下载会话已损坏".to_string())?;
        sessions.insert(transfer_id.clone(), Arc::clone(&handle));
    }

    spawn_progress_emitter(app, transfer_id.clone(), Arc::clone(&handle));

    Ok(DesktopDownloadSession {
        transfer_id,
        file_name,
        local_path: destination.to_string_lossy().to_string(),
    })
}

#[tauri::command]
async fn desktop_download_file(
    source_url: String,
    remote: String,
    remote_path: String,
    file_name: String,
) -> Result<DesktopTransferResult, String> {
    let relative_path = build_relative_file_path(&remote, &remote_path, &file_name);
    let destination = downloads_root_dir()?.join(relative_path);
    let destination_for_task = destination.clone();

    tauri::async_runtime::spawn_blocking(move || download_to_path(&source_url, &destination_for_task))
        .await
        .map_err(|error| format!("桌面下载任务失败: {error}"))??;

    Ok(DesktopTransferResult {
        file_name,
        local_path: destination.to_string_lossy().to_string(),
    })
}

#[tauri::command]
async fn desktop_prepare_preview_file(
    source_url: String,
    remote: String,
    remote_path: String,
    file_name: String,
) -> Result<DesktopTransferResult, String> {
    let relative_path = build_relative_file_path(&remote, &remote_path, &file_name);
    let destination = preview_cache_root_dir()?.join(relative_path);

    if !destination.exists() {
        let destination_for_task = destination.clone();
        tauri::async_runtime::spawn_blocking(move || {
            download_to_path(&source_url, &destination_for_task)
        })
        .await
        .map_err(|error| format!("本地预览缓存任务失败: {error}"))??;
    }

    Ok(DesktopTransferResult {
        file_name,
        local_path: destination.to_string_lossy().to_string(),
    })
}

#[tauri::command]
fn desktop_start_preview_stream(
    app: tauri::AppHandle,
    state: tauri::State<'_, DesktopRuntimeState>,
    source_url: String,
    remote: String,
    remote_path: String,
    file_name: String,
) -> Result<DesktopPreviewSession, String> {
    let relative_path = build_relative_file_path(&remote, &remote_path, &file_name);
    let destination = preview_cache_root_dir()?.join(relative_path);
    let transfer_key = destination.to_string_lossy().to_string();

    let handle = {
        let mut transfers = state
            .preview_transfers
            .lock()
            .map_err(|_| "本地预览缓存状态已损坏".to_string())?;

        if let Some(existing) = transfers.get(&transfer_key) {
            Arc::clone(existing)
        } else {
            let handle = Arc::new(TransferHandle::new_preview(
                file_name.clone(),
                source_url,
                destination.clone(),
            ));
            transfers.insert(transfer_key, Arc::clone(&handle));
            handle
        }
    };

    spawn_transfer(Arc::clone(&handle), None, 1);

    let transfer_id = format!(
        "{}-{}",
        std::process::id(),
        state.next_transfer_id.fetch_add(1, Ordering::SeqCst)
    );

    {
        let mut sessions = state
            .preview_sessions
            .lock()
            .map_err(|_| "本地预览会话已损坏".to_string())?;
        sessions.insert(transfer_id.clone(), Arc::clone(&handle));
    }

    let status = snapshot_transfer_status(&transfer_id, &handle)?;

    spawn_progress_emitter(app, transfer_id.clone(), Arc::clone(&handle));

    Ok(DesktopPreviewSession {
        transfer_id: transfer_id.clone(),
        stream_url: format!("http://127.0.0.1:{}/preview/{}", state.preview_server_port, transfer_id),
        local_path: destination.to_string_lossy().to_string(),
        ready_for_preview: status.ready_for_preview,
    })
}

#[tauri::command]
fn desktop_get_transfer_status(
    state: tauri::State<'_, DesktopRuntimeState>,
    transfer_id: String,
) -> Result<DesktopTransferStatus, String> {
    let handle = {
        let preview_handle = state
            .preview_sessions
            .lock()
            .map_err(|_| "本地预览会话已损坏".to_string())?
            .get(&transfer_id)
            .cloned();

        if let Some(handle) = preview_handle {
            handle
        } else {
            state
                .download_sessions
                .lock()
                .map_err(|_| "本地下载会话已损坏".to_string())?
                .get(&transfer_id)
                .cloned()
                .ok_or_else(|| "未找到桌面传输任务".to_string())?
        }
    };

    snapshot_transfer_status(&transfer_id, &handle)
}

fn main() {
    let mut context = tauri::generate_context!();
    let runtime_state = DesktopRuntimeState::new()
        .expect("failed to start local desktop preview runtime");

    match load_desktop_client_config() {
        Ok(config) => {
            if let Err(error) = apply_process_proxy_env(&config) {
                eprintln!("failed to apply process proxy config: {error}");
            }
        }
        Err(error) => {
            eprintln!("failed to load desktop client config: {error}");
        }
    }

    if let Err(error) = apply_saved_proxy(&mut context) {
        eprintln!("failed to apply desktop proxy config: {error}");
    }

    tauri::Builder::default()
        .plugin(tauri_plugin_dialog::init())
        .plugin(tauri_plugin_updater::Builder::new().build())
        .plugin(tauri_plugin_process::init())
        .manage(runtime_state)
        .invoke_handler(tauri::generate_handler![
            get_desktop_client_config,
            get_default_desktop_download_dir,
            pick_desktop_download_dir,
            save_desktop_client_config,
            restart_desktop_app,
            desktop_start_download,
            desktop_download_file,
            desktop_prepare_preview_file,
            desktop_start_preview_stream,
            desktop_get_transfer_status
        ])
        .run(context)
        .expect("error while running MistRelay desktop shell");
}
