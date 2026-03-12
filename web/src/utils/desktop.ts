import { check, type Update } from '@tauri-apps/plugin-updater'
import { relaunch } from '@tauri-apps/plugin-process'
import { isDesktopShell } from '@/utils/runtime'

export interface DesktopProxyConfig {
  enabled: boolean
  url: string
}

export interface DesktopClientConfig {
  proxy: DesktopProxyConfig
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
  progressPercent: number
  state: 'pending' | 'downloading' | 'ready' | 'completed' | 'error'
  readyForPreview: boolean
  error?: string
}

const DEFAULT_DESKTOP_CLIENT_CONFIG: DesktopClientConfig = {
  proxy: {
    enabled: false,
    url: '',
  },
}

function getTauriInvoke() {
  return window.__TAURI__?.core?.invoke
}

async function invokeDesktopCommand<T>(
  command: string,
  args?: Record<string, unknown>,
): Promise<T> {
  if (!isDesktopShell()) {
    throw new Error('当前不是桌面客户端环境')
  }

  const invoke = getTauriInvoke()
  if (!invoke) {
    throw new Error('桌面客户端 API 不可用')
  }

  return invoke<T>(command, args)
}

export async function getDesktopClientConfig(): Promise<DesktopClientConfig> {
  if (!isDesktopShell()) {
    return { ...DEFAULT_DESKTOP_CLIENT_CONFIG }
  }

  return invokeDesktopCommand<DesktopClientConfig>('get_desktop_client_config')
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
}

export async function checkForUpdate(): Promise<{ result: UpdateCheckResult; update: Update | null }> {
  if (!isDesktopShell()) {
    return { result: { available: false }, update: null }
  }

  const update = await check()

  if (!update) {
    return { result: { available: false }, update: null }
  }

  return {
    result: {
      available: true,
      version: update.version,
      body: update.body ?? undefined,
      date: update.date ?? undefined,
    },
    update,
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
