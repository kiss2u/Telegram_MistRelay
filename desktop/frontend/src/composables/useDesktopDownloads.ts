import { computed, ref } from 'vue'
import { ElMessage } from 'element-plus'
import {
  getDesktopTransferStatus,
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

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

function getDesktopDownloadStateScore(value: DesktopTransferStatus['state']): number {
  if (value === 'downloading' || value === 'pending') return 0
  if (value === 'completed') return 1
  return 2
}

async function monitorDesktopDownload(transferId: string, pathKey: string) {
  let successNotified = false

  try {
    while (true) {
      const status = await getDesktopTransferStatus(transferId)
      desktopDownloadStatuses.value = {
        ...desktopDownloadStatuses.value,
        [transferId]: status,
      }

      if (status.state === 'completed') {
        downloadingPaths.value = {
          ...downloadingPaths.value,
          [pathKey]: false,
        }
        if (!successNotified) {
          ElMessage.success(`已下载到本地: ${status.localPath}`)
          successNotified = true
        }
        return
      }

      if (status.state === 'error') {
        downloadingPaths.value = {
          ...downloadingPaths.value,
          [pathKey]: false,
        }
        ElMessage.error(status.error || '桌面端下载失败')
        return
      }

      await sleep(350)
    }
  } catch (err: any) {
    console.error('轮询桌面下载进度失败:', err)
    downloadingPaths.value = {
      ...downloadingPaths.value,
      [pathKey]: false,
    }
    ElMessage.error(err.message || '轮询桌面下载进度失败')
  }
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

    void monitorDesktopDownload(session.transferId, params.pathKey)
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
