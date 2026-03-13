import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  startDesktopDownload,
  type DesktopTransferStatus,
} from '@/utils/desktop'

interface StartDesktopDownloadParams {
  sourceUrl: string
  remote: string
  remotePath: string
  fileName: string
  pathKey: string
}

const downloadingPaths = ref<Record<string, boolean>>({})
const desktopDownloadStatuses = ref<Record<string, DesktopTransferStatus>>({})
const transferPathKeys: Record<string, string> = {}
const notifiedTransfers = new Set<string>()

let listenerActive = false

function handleTransferProgress(status: DesktopTransferStatus) {
  desktopDownloadStatuses.value = {
    ...desktopDownloadStatuses.value,
    [status.transferId]: status,
  }

  if (notifiedTransfers.has(status.transferId)) return

  const pathKey = transferPathKeys[status.transferId]

  if (status.state === 'completed') {
    notifiedTransfers.add(status.transferId)
    if (pathKey) {
      downloadingPaths.value = { ...downloadingPaths.value, [pathKey]: false }
    }
    ElMessage.success(`已下载到本地: ${status.localPath}`)
  } else if (status.state === 'error') {
    notifiedTransfers.add(status.transferId)
    if (pathKey) {
      downloadingPaths.value = { ...downloadingPaths.value, [pathKey]: false }
    }
    ElMessage.error(status.error || '桌面端下载失败')
  }
}

function ensureProgressListener() {
  if (listenerActive) return
  listenerActive = true

  const listen = window.__TAURI__?.event?.listen
  if (!listen) return

  listen<DesktopTransferStatus>('desktop-transfer-progress', (event) => {
    handleTransferProgress(event.payload)
  })
}

function getDesktopDownloadStateScore(value: DesktopTransferStatus['state']): number {
  if (value === 'downloading' || value === 'pending') return 0
  if (value === 'completed') return 1
  return 2
}

const desktopDownloadList = computed(() => {
  return Object.values(desktopDownloadStatuses.value).sort((a, b) => {
    return getDesktopDownloadStateScore(a.state) - getDesktopDownloadStateScore(b.state)
  })
})

const desktopDownloadStats = computed(() => {
  return desktopDownloadList.value.reduce(
    (acc, task) => {
      if (task.state === 'completed') acc.completed += 1
      else if (task.state === 'error') acc.failed += 1
      else acc.active += 1
      return acc
    },
    { total: desktopDownloadList.value.length, active: 0, completed: 0, failed: 0 }
  )
})

function getDesktopDownloadLabel(task: DesktopTransferStatus): string {
  if (task.state === 'completed') return '已完成'
  if (task.state === 'error') return '失败'
  if (task.state === 'pending') return '等待中'
  return '下载中'
}

function getDesktopDownloadTagType(task: DesktopTransferStatus): 'success' | 'danger' | 'warning' | 'info' {
  if (task.state === 'completed') return 'success'
  if (task.state === 'error') return 'danger'
  if (task.state === 'pending') return 'info'
  return 'warning'
}

function getDesktopDownloadProgressStatus(task: DesktopTransferStatus): '' | 'success' | 'exception' | 'warning' {
  if (task.state === 'completed') return 'success'
  if (task.state === 'error') return 'exception'
  return 'warning'
}

function formatDesktopBytes(bytes: number | undefined): string {
  if (!bytes || bytes === 0) return '0 B'
  const units = ['B', 'KB', 'MB', 'GB', 'TB']
  const exponent = Math.min(Math.floor(Math.log(bytes) / Math.log(1024)), units.length - 1)
  return `${parseFloat((bytes / 1024 ** exponent).toFixed(2))} ${units[exponent]}`
}

function formatDesktopDownloadMeta(task: DesktopTransferStatus): string {
  const downloaded = formatDesktopBytes(task.downloadedBytes)
  if (task.totalBytes && task.totalBytes > 0) {
    return `${downloaded} / ${formatDesktopBytes(task.totalBytes)}`
  }
  return downloaded
}

async function startTrackedDesktopDownload(params: StartDesktopDownloadParams): Promise<boolean> {
  if (downloadingPaths.value[params.pathKey]) {
    return false
  }

  downloadingPaths.value = {
    ...downloadingPaths.value,
    [params.pathKey]: true,
  }

  try {
    const session = await startDesktopDownload({
      sourceUrl: params.sourceUrl,
      remote: params.remote,
      remotePath: params.remotePath,
      fileName: params.fileName,
    })

    transferPathKeys[session.transferId] = params.pathKey

    desktopDownloadStatuses.value = {
      ...desktopDownloadStatuses.value,
      [session.transferId]: {
        transferId: session.transferId,
        fileName: session.fileName,
        localPath: session.localPath,
        downloadedBytes: 0,
        totalBytes: undefined,
        progressPercent: 0,
        state: 'pending',
        readyForPreview: false,
      },
    }

    return true
  } catch (err: any) {
    console.error('桌面端下载失败:', err)
    downloadingPaths.value = {
      ...downloadingPaths.value,
      [params.pathKey]: false,
    }
    ElMessage.error(err.message || '桌面端下载失败')
    return false
  }
}

export function useDesktopDownloads() {
  ensureProgressListener()

  return {
    downloadingPaths,
    desktopDownloadList,
    desktopDownloadStats,
    getDesktopDownloadLabel,
    getDesktopDownloadTagType,
    getDesktopDownloadProgressStatus,
    formatDesktopDownloadMeta,
    startTrackedDesktopDownload,
  }
}
