import axios from 'axios'
import type {
  ServerStatus,
  DownloadsResponse,
  DockerStatus,
  DockerRestartResponse,
  DockerLogsResponse,
  ConfigResponse,
  ConfigUpdateResponse,
  SystemResourcesResponse,
  UploadRecord
} from '@/types/api'
import {
  clearAuthToken,
  getApiBaseUrl,
  getAuthToken,
  redirectToLogin,
  resolveServerUrl,
} from '@/utils/runtime'

export const api = axios.create({
  timeout: 60000,
  headers: {
    'Content-Type': 'application/json'
  }
})

api.interceptors.request.use((config) => {
  config.baseURL = getApiBaseUrl()

  const token = getAuthToken()
  if (token) {
    config.headers.Authorization = `Bearer ${token}`
  }
  return config
})

api.interceptors.response.use(
  (response) => response,
  (error) => {
    if (error.response?.status === 401) {
      clearAuthToken()
      const isLoginRoute = window.location.pathname === '/login' || window.location.hash.startsWith('#/login')
      if (!isLoginRoute) {
        redirectToLogin()
      }
    }
    return Promise.reject(error)
  }
)

export function getStatus(): Promise<ServerStatus> {
  return api.get<ServerStatus>('/status').then(response => response.data)
}

export function getDownloads(limit = 100, grouped = true): Promise<DownloadsResponse> {
  return api.get<DownloadsResponse>('/downloads', {
    params: { limit, grouped }
  }).then(response => response.data)
}

export function getDockerStatus(): Promise<DockerStatus> {
  return api.get<DockerStatus>('/system/docker/status').then(response => response.data)
}

export function restartDocker(): Promise<DockerRestartResponse> {
  return api.post<DockerRestartResponse>('/system/docker/restart').then(response => response.data)
}

export function getDockerLogs(lines = 100): Promise<DockerLogsResponse> {
  return api.get<DockerLogsResponse>('/system/docker/logs', {
    params: { lines }
  }).then(response => response.data)
}

export function getSystemResources(): Promise<SystemResourcesResponse> {
  return api.get<SystemResourcesResponse>('/system/resources').then(response => response.data)
}

export function getConfig(category?: string): Promise<ConfigResponse> {
  return api.get<ConfigResponse>('/config', {
    params: category ? { category } : {}
  }).then(response => response.data)
}

export function updateConfig(config: Record<string, any>): Promise<ConfigUpdateResponse> {
  return api.post<ConfigUpdateResponse>('/config', config).then(response => response.data)
}

export function reloadConfig(): Promise<ConfigUpdateResponse> {
  return api.post<ConfigUpdateResponse>('/config/reload').then(response => response.data)
}

export interface QueueStatus {
  success: boolean
  current_processing: any | null
  waiting_count: number
  waiting_items: any[]
  queue_size: number
  error?: string
}

export function getQueue(): Promise<QueueStatus> {
  return api.get<QueueStatus>('/queue').then(response => response.data)
}

export interface TrendPoint {
  timestamp: number
  upload: number
  download: number
  io: number
}

export interface TrendResponse {
  success: boolean
  data: TrendPoint[]
  error?: string
}

export function getSystemTrend(): Promise<TrendResponse> {
  return api.get<TrendResponse>('/monitor/trend').then(response => response.data)
}

export interface DownloadStatistics {
  total: number
  completed: number
  downloading: number
  failed: number
  pending: number
  waiting: number
  total_size: number
  completed_size: number
}

export interface DownloadStatisticsResponse {
  success: boolean
  data: DownloadStatistics
  error?: string
}

export function getDownloadStatistics(): Promise<DownloadStatisticsResponse> {
  return api.get<DownloadStatisticsResponse>('/downloads/statistics').then(response => response.data)
}

export interface DeleteAllDownloadsResponse {
  success: boolean
  message?: string
  data?: {
    deleted_downloads: number
    deleted_media: number
  }
  error?: string
}

export function deleteAllDownloads(): Promise<DeleteAllDownloadsResponse> {
  return api.delete<DeleteAllDownloadsResponse>('/downloads/all').then(response => response.data)
}

export interface UploadStatistics {
  total: number
  uploading: number
  completed: number
  failed: number
  pending: number
  cleaned: number
}

export interface UploadStatisticsResponse {
  success: boolean
  data: UploadStatistics
  error?: string
}

export function getUploadStatistics(): Promise<UploadStatisticsResponse> {
  return api.get<UploadStatisticsResponse>('/uploads/statistics').then(response => response.data)
}

export interface UploadsResponse {
  success: boolean
  limit: number
  count: number
  data: UploadRecord[]
  error?: string
}

export function getUploads(limit = 100, status?: string, uploadTarget?: string): Promise<UploadsResponse> {
  return api.get<UploadsResponse>('/uploads', {
    params: { limit, status, upload_target: uploadTarget }
  }).then(response => response.data)
}

// ==================== 下载任务控制 API ====================

export interface TaskControlResponse {
  success: boolean
  message?: string
  new_gid?: string
  error?: string
}

export function retryDownload(gid: string): Promise<TaskControlResponse> {
  return api.post<TaskControlResponse>(`/downloads/${gid}/retry`).then(response => response.data)
}

export function deleteDownload(gid: string): Promise<TaskControlResponse> {
  return api.delete<TaskControlResponse>(`/downloads/${gid}`).then(response => response.data)
}

export interface DeleteRecordResponse {
  success: boolean
  message?: string
  data?: {
    download_deleted: boolean
    upload_count: number
    media_deleted: boolean
    file_deleted: boolean
    local_path?: string
  }
  error?: string
}

export function deleteDownloadRecord(downloadId: number, deleteFile: boolean = true): Promise<DeleteRecordResponse> {
  return api.delete<DeleteRecordResponse>(`/downloads/record/${downloadId}`, {
    params: { delete_file: deleteFile }
  }).then(response => response.data)
}

// ==================== 上传任务控制 API ====================

export function retryUpload(uploadId: number): Promise<TaskControlResponse> {
  return api.post<TaskControlResponse>(`/uploads/${uploadId}/retry`).then(response => response.data)
}

export function deleteUpload(uploadId: number): Promise<TaskControlResponse> {
  return api.delete<TaskControlResponse>(`/uploads/${uploadId}`).then(response => response.data)
}

// ==================== Rclone 配置管理 API ====================

export interface RcloneConfigResponse {
  success: boolean
  content?: string
  file_path?: string
  exists?: boolean
  message?: string
  backup_path?: string
  error?: string
}

export function getRcloneConfig(): Promise<RcloneConfigResponse> {
  return api.get<RcloneConfigResponse>('/rclone/config').then(response => response.data)
}

export function saveRcloneConfig(content: string): Promise<RcloneConfigResponse> {
  return api.post<RcloneConfigResponse>('/rclone/config', { content }).then(response => response.data)
}

export interface RcloneRemote {
  name: string
  type: string
}

export interface RcloneRemotesResponse {
  success: boolean
  remotes?: RcloneRemote[]
  error?: string
}

export function getRcloneRemotes(): Promise<RcloneRemotesResponse> {
  return api.get<RcloneRemotesResponse>('/rclone/remotes').then(response => response.data)
}

export interface DriveItem {
  name: string
  path: string
  size?: number
  mimeType?: string
  modTime?: string
  isDir: boolean
  id?: string  // 云盘文件ID(如OneDrive的文件ID)
}

export interface DriveBrowseResponse {
  success: boolean
  remote?: string
  path?: string
  items?: DriveItem[]
  error?: string
}

export function browseDrive(remote: string, path: string = '/'): Promise<DriveBrowseResponse> {
  return api.get<DriveBrowseResponse>('/rclone/browse', {
    params: { remote, path }
  }).then(response => response.data)
}

export interface DriveUsageInfo {
  total?: number | null
  used?: number | null
  free?: number | null
  trashed?: number | null
  other?: number | null
  objects?: number | null
}

export interface DriveUsageResponse {
  success: boolean
  supported?: boolean
  remote?: string
  data?: DriveUsageInfo
  error?: string
}

export function getDriveUsage(remote: string): Promise<DriveUsageResponse> {
  return api.get<DriveUsageResponse>('/rclone/about', {
    params: { remote }
  }).then(response => response.data)
}

export interface ThumbnailResponse {
  success: boolean
  thumbnail_url?: string
  error?: string
}

export function getThumbnail(remote: string, path: string, type: string, dir?: string, id?: string): Promise<ThumbnailResponse> {
  return api.get<ThumbnailResponse>('/rclone/thumbnail', {
    params: { remote, path, type, dir, id }
  }).then(response => ({
    ...response.data,
    thumbnail_url: response.data.thumbnail_url
      ? resolveServerUrl(response.data.thumbnail_url)
      : response.data.thumbnail_url
  }))
}

export interface DeleteFileResponse {
  success: boolean
  message?: string
  error?: string
}

export function deleteFile(remote: string, path: string, isDir: boolean = false): Promise<DeleteFileResponse> {
  return api.delete<DeleteFileResponse>('/rclone/file', {
    params: {
      remote,
      path,
      is_dir: isDir
    }
  }).then(response => response.data)
}

// ==================== 日志管理 API ====================

export interface LogFile {
  name: string
  path: string
  size: number
  modified: string
}

export interface LogFilesResponse {
  success: boolean
  files: LogFile[]
  error?: string
}

export interface LogContentResponse {
  success: boolean
  total: number
  lines: string[]
  error?: string
}

export function getLogFiles(): Promise<LogFilesResponse> {
  return api.get<LogFilesResponse>('/logs/files').then(r => r.data)
}

export function getLogContent(params: {
  file?: string
  tail?: number
  level?: string
  keyword?: string
}): Promise<LogContentResponse> {
  return api.get<LogContentResponse>('/logs', { params }).then(r => r.data)
}

export function getLogDownloadUrl(filename: string): string {
  const token = getAuthToken()
  return resolveServerUrl(
    `/api/logs/download/${encodeURIComponent(filename)}?token=${encodeURIComponent(token)}`
  )
}

// ==================== 用户认证 API ====================

export interface ChangePasswordResponse {
  success: boolean
  message?: string
  error?: string
}

export function changePassword(oldPassword: string, newPassword: string): Promise<ChangePasswordResponse> {
  return api.post<ChangePasswordResponse>('/auth/password', {
    old_password: oldPassword,
    new_password: newPassword,
  }).then(r => r.data)
}
