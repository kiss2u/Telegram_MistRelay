import { check, type Update } from '@tauri-apps/plugin-updater'
import { relaunch } from '@tauri-apps/plugin-process'

export interface DesktopProxyConfig {
  enabled: boolean
  url: string
}

export interface DesktopDownloadConfig {
  downloadDir: string
  maxConcurrentDownloads: number
  threadsPerDownload: number
}

export interface DesktopClientConfig {
  proxy: DesktopProxyConfig
  download: DesktopDownloadConfig
}

export const DEFAULT_DOWNLOAD_CONFIG: DesktopDownloadConfig = {
  downloadDir: '',
  maxConcurrentDownloads: 3,
  threadsPerDownload: 4,
}

export interface DesktopTransferResult {
  fileName: string
  localPath: string
}

export interface DesktopDownloadSession {
  transferId: string
  fileName: string
  localPath: string
}

export interface DesktopPreviewSession {
  transferId: string
  streamUrl: string
  localPath: string
  readyForPreview: boolean
}

export interface DesktopTransferStatus {
  transferId: string
  fileName: string
  localPath: string
  downloadedBytes: number
  totalBytes?: number
  downloadSpeed: number
  progressPercent: number
  state: 'pending' | 'downloading' | 'ready' | 'completed' | 'error' | 'cancelling' | 'cancelled'
  readyForPreview: boolean
  error?: string
}

const DEFAULT_DESKTOP_CLIENT_CONFIG: DesktopClientConfig = {
  proxy: {
    enabled: false,
    url: '',
  },
  download: { ...DEFAULT_DOWNLOAD_CONFIG },
}

function getTauriInvoke() {
  return window.__TAURI__?.core?.invoke
}

async function invokeDesktopCommand<T>(
  command: string,
  args?: Record<string, unknown>,
): Promise<T> {
  const invoke = getTauriInvoke()
  if (!invoke) {
    throw new Error('桌面客户端 API 不可用')
  }

  return invoke<T>(command, args)
}

export async function getDesktopClientConfig(): Promise<DesktopClientConfig> {
  return invokeDesktopCommand<DesktopClientConfig>('get_desktop_client_config')
}

export async function getDefaultDesktopDownloadDir(): Promise<string> {
  return invokeDesktopCommand<string>('get_default_desktop_download_dir')
}

export async function pickDesktopDownloadDir(currentDir?: string): Promise<string | null> {
  return invokeDesktopCommand<string | null>('pick_desktop_download_dir', { currentDir })
}

export async function saveDesktopClientConfig(config: DesktopClientConfig): Promise<void> {
  await invokeDesktopCommand('save_desktop_client_config', { config })
}

export async function restartDesktopApp(): Promise<void> {
  await invokeDesktopCommand('restart_desktop_app')
}

export async function downloadDesktopFile(payload: {
  sourceUrl: string
  remote: string
  remotePath: string
  fileName: string
}): Promise<DesktopTransferResult> {
  return invokeDesktopCommand<DesktopTransferResult>('desktop_download_file', payload)
}

export async function startDesktopDownload(payload: {
  sourceUrl: string
  remote: string
  remotePath: string
  fileName: string
}): Promise<DesktopDownloadSession> {
  return invokeDesktopCommand<DesktopDownloadSession>('desktop_start_download', payload)
}

export async function prepareDesktopPreviewFile(payload: {
  sourceUrl: string
  remote: string
  remotePath: string
  fileName: string
}): Promise<DesktopTransferResult> {
  return invokeDesktopCommand<DesktopTransferResult>('desktop_prepare_preview_file', payload)
}

export async function startDesktopPreviewStream(payload: {
  sourceUrl: string
  remote: string
  remotePath: string
  fileName: string
}): Promise<DesktopPreviewSession> {
  return invokeDesktopCommand<DesktopPreviewSession>('desktop_start_preview_stream', payload)
}

export async function getDesktopTransferStatus(transferId: string): Promise<DesktopTransferStatus> {
  return invokeDesktopCommand<DesktopTransferStatus>('desktop_get_transfer_status', { transferId })
}

export async function cancelDesktopDownload(transferId: string): Promise<DesktopTransferStatus> {
  return invokeDesktopCommand<DesktopTransferStatus>('desktop_cancel_download', { transferId })
}

export async function removeDesktopDownloadSession(transferId: string): Promise<void> {
  await invokeDesktopCommand('desktop_remove_download_session', { transferId })
}

export async function retryDesktopDownload(transferId: string): Promise<DesktopTransferStatus> {
  return invokeDesktopCommand<DesktopTransferStatus>('desktop_retry_download', { transferId })
}

export async function cancelDesktopPreview(transferId: string): Promise<void> {
  await invokeDesktopCommand('desktop_cancel_preview', { transferId })
}

export async function openDesktopLocalFile(localPath: string): Promise<void> {
  await invokeDesktopCommand('desktop_open_local_file', { localPath })
}

export async function showDesktopLocalFileInFolder(localPath: string): Promise<void> {
  await invokeDesktopCommand('desktop_show_local_file_in_folder', { localPath })
}

export function toDesktopAssetUrl(localPath: string): string {
  const convertFileSrc =
    window.__TAURI__?.core?.convertFileSrc ||
    (window.__TAURI_INTERNALS__ as { convertFileSrc?: (filePath: string, protocol?: string) => string } | undefined)
      ?.convertFileSrc

  if (!convertFileSrc) {
    throw new Error('桌面客户端本地文件协议不可用')
  }

  return convertFileSrc(localPath)
}

export function isValidDesktopProxyUrl(value: string): boolean {
  try {
    const parsed = new URL(value.trim())
    return parsed.protocol === 'http:' || parsed.protocol === 'socks5:'
  } catch {
    return false
  }
}

export interface UpdateProgress {
  downloaded: number
  total: number | null
  done: boolean
}

export interface UpdateCheckResult {
  available: boolean
  version?: string
  body?: string
  date?: string
  message?: string
  installable?: boolean
  manualUrl?: string
  source?: 'native' | 'manifest'
}

interface PublishedUpdateInfo {
  version: string
  notes?: string
  pubDate?: string
  downloadUrl?: string
}

function normalizeVersion(value: string): string[] {
  return value
    .trim()
    .replace(/^v/i, '')
    .split(/[\.-]/)
    .filter(Boolean)
}

function compareVersions(left: string, right: string): number {
  const leftParts = normalizeVersion(left)
  const rightParts = normalizeVersion(right)
  const maxLength = Math.max(leftParts.length, rightParts.length)

  for (let index = 0; index < maxLength; index += 1) {
    const rawLeft = leftParts[index] ?? '0'
    const rawRight = rightParts[index] ?? '0'
    const leftNumber = Number(rawLeft)
    const rightNumber = Number(rawRight)
    const bothNumeric = Number.isFinite(leftNumber) && Number.isFinite(rightNumber)

    if (bothNumeric) {
      if (leftNumber > rightNumber) return 1
      if (leftNumber < rightNumber) return -1
      continue
    }

    if (rawLeft > rawRight) return 1
    if (rawLeft < rawRight) return -1
  }

  return 0
}

async function getPublishedUpdateInfo(): Promise<PublishedUpdateInfo> {
  return invokeDesktopCommand<PublishedUpdateInfo>('desktop_get_published_update_info')
}

async function getConfiguredUpdaterProxy(): Promise<string | undefined> {
  try {
    const config = await getDesktopClientConfig()
    if (!config.proxy.enabled) {
      return undefined
    }

    const proxy = config.proxy.url.trim()
    if (!proxy || !isValidDesktopProxyUrl(proxy)) {
      return undefined
    }

    return proxy
  } catch {
    return undefined
  }
}

export async function checkForUpdate(): Promise<{ result: UpdateCheckResult; update: Update | null }> {
  try {
    const proxy = await getConfiguredUpdaterProxy()
    const update = await check(proxy ? { proxy } : undefined)

    if (!update) {
      return {
        result: {
          available: false,
          installable: true,
          message: '当前已是最新版本',
          source: 'native',
        },
        update: null,
      }
    }

    return {
      result: {
        available: true,
        version: update.version,
        body: update.body ?? undefined,
        date: update.date ?? undefined,
        installable: true,
        source: 'native',
      },
      update,
    }
  } catch (nativeError: any) {
    const nativeMessage = nativeError?.message?.trim() || '内置自动更新校验失败'

    try {
      const published = await getPublishedUpdateInfo()
      const comparison = compareVersions(published.version, __APP_VERSION__)

      if (comparison <= 0) {
        return {
          result: {
            available: false,
            version: published.version,
            body: published.notes,
            date: published.pubDate,
            installable: false,
            manualUrl: published.downloadUrl,
            message: '当前已是最新版本',
            source: 'manifest',
          },
          update: null,
        }
      }

      return {
        result: {
          available: true,
          version: published.version,
          body: published.notes,
          date: published.pubDate,
          installable: false,
          manualUrl: published.downloadUrl,
          message: `发现 v${published.version}，但当前客户端无法自动更新，请手动下载安装包升级。原因：${nativeMessage}`,
          source: 'manifest',
        },
        update: null,
      }
    } catch (manifestError: any) {
      const manifestMessage = manifestError?.message || '发布清单校验失败'
      throw new Error(`${nativeMessage}；${manifestMessage}`)
    }
  }
}

export async function downloadAndInstallUpdate(
  update: Update,
  onProgress?: (progress: UpdateProgress) => void,
): Promise<void> {
  let downloaded = 0
  let total: number | null = null

  await update.downloadAndInstall((event) => {
    switch (event.event) {
      case 'Started':
        total = event.data.contentLength ?? null
        onProgress?.({ downloaded: 0, total, done: false })
        break
      case 'Progress':
        downloaded += event.data.chunkLength
        onProgress?.({ downloaded, total, done: false })
        break
      case 'Finished':
        onProgress?.({ downloaded, total, done: true })
        break
    }
  })

  await relaunch()
}
