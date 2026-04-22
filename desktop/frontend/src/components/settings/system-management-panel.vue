<template>
  <div class="system-page">
    <el-tabs v-model="activeTabModel" class="system-tabs">
      <el-tab-pane label="容器管理" name="docker">
        <el-row :gutter="20">
          <el-col :xs="24" :lg="12">
            <el-card shadow="hover" class="mb-6">
              <template #header>
                <div class="flex justify-between items-center">
                  <span>Docker容器状态</span>
                  <el-button
                    :icon="Refresh"
                    circle
                    size="small"
                    @click="fetchDockerStatus"
                    :loading="loadingStatus"
                  />
                </div>
              </template>

              <el-skeleton v-if="loadingStatus" :rows="5" animated />

              <div v-else-if="dockerStatus">
                <el-descriptions :column="1" border size="small">
                  <el-descriptions-item label="运行环境">
                    <el-tag :type="dockerStatus.in_docker ? 'success' : 'info'" size="small">
                      {{ dockerStatus.in_docker ? 'Docker容器内' : '非Docker环境' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="容器名称">
                    {{ dockerStatus.container_name || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="运行状态">
                    <el-tag
                      :type="getStatusType(dockerStatus.status)"
                      size="small"
                    >
                      {{ dockerStatus.status || '-' }}
                    </el-tag>
                  </el-descriptions-item>
                  <el-descriptions-item label="镜像名称">
                    {{ dockerStatus.image || '-' }}
                  </el-descriptions-item>
                  <el-descriptions-item label="创建时间">
                    {{ formatDate(dockerStatus.created) }}
                  </el-descriptions-item>
                </el-descriptions>

                <div v-if="dockerStatus.error" class="mt-4">
                  <el-alert
                    :title="dockerStatus.error"
                    type="warning"
                    :closable="false"
                  />
                </div>
              </div>

              <el-empty v-else description="无法获取容器状态" />
            </el-card>
          </el-col>

          <el-col :xs="24" :lg="12">
            <el-card shadow="hover" class="mb-6">
              <template #header>
                <span>容器控制</span>
              </template>

              <div class="control-actions">
                <el-button
                  type="primary"
                  :icon="RefreshRight"
                  @click="handleRestart"
                  :loading="restarting"
                  :disabled="!dockerStatus?.in_docker"
                  block
                  size="large"
                >
                  重启容器（热重载）
                </el-button>

                <el-alert
                  v-if="!dockerStatus?.in_docker"
                  title="当前不在Docker容器内运行，无法执行容器操作"
                  type="info"
                  :closable="false"
                  class="mt-4"
                />

                <div v-if="restartMessage" class="mt-4">
                  <el-alert
                    :title="restartMessage"
                    :type="restartSuccess ? 'success' : 'error'"
                    :closable="true"
                    @close="restartMessage = ''"
                  />
                </div>
              </div>
            </el-card>
          </el-col>
        </el-row>

        <el-card shadow="hover">
          <template #header>
            <div class="flex justify-between items-center">
              <span>容器日志</span>
              <div class="flex gap-2">
                <el-select
                  v-model="dockerLogLines"
                  @change="handleDockerLogLinesChange"
                  style="width: 120px"
                  size="small"
                  :disabled="wsConnected"
                >
                  <el-option label="50 行" :value="50" />
                  <el-option label="100 行" :value="100" />
                  <el-option label="200 行" :value="200" />
                  <el-option label="500 行" :value="500" />
                </el-select>
                <el-button
                  v-if="!wsConnected"
                  :icon="VideoPlay"
                  circle
                  size="small"
                  @click="startLogStream"
                  :loading="connecting"
                  title="开始实时日志"
                />
                <el-button
                  v-else
                  :icon="VideoPause"
                  circle
                  size="small"
                  @click="stopLogStream"
                  title="停止实时日志"
                />
                <el-button
                  :icon="Refresh"
                  circle
                  size="small"
                  @click="fetchDockerLogs"
                  :loading="loadingDockerLogs"
                  :disabled="wsConnected"
                  title="刷新日志"
                />
                <el-button
                  :icon="Delete"
                  circle
                  size="small"
                  @click="clearDockerLogs"
                  title="清空日志"
                />
              </div>
            </div>
          </template>

          <el-skeleton v-if="loadingDockerLogs && !wsConnected" :rows="10" animated />

          <div v-else class="logs-container" ref="dockerLogsContainerRef">
            <pre class="logs-content">{{ dockerLogs }}</pre>
          </div>

          <el-empty v-if="!dockerLogs && !wsConnected" description="无法获取容器日志" />
        </el-card>
      </el-tab-pane>

      <el-tab-pane label="系统日志" name="app-logs">
        <el-card shadow="hover" class="mb-4">
          <div class="toolbar">
            <div class="toolbar-left">
              <el-select v-model="selectedFile" placeholder="当前日志" clearable style="width: 220px" size="default" @change="fetchAppLogs">
                <el-option v-for="f in logFiles" :key="f.name" :label="`${f.name} (${formatSize(f.size)})`" :value="f.name" />
              </el-select>

              <el-select v-model="levelFilter" placeholder="全部级别" clearable style="width: 130px" size="default" @change="fetchAppLogs">
                <el-option label="ERROR" value="ERROR" />
                <el-option label="WARNING" value="WARNING" />
                <el-option label="INFO" value="INFO" />
                <el-option label="DEBUG" value="DEBUG" />
              </el-select>

              <el-input v-model="keyword" placeholder="关键词搜索" clearable style="width: 200px" size="default" @keyup.enter="fetchAppLogs" @clear="fetchAppLogs">
                <template #prefix>
                  <el-icon><Search /></el-icon>
                </template>
              </el-input>

              <el-select v-model="tailCount" style="width: 120px" size="default" @change="fetchAppLogs">
                <el-option label="最新 100 行" :value="100" />
                <el-option label="最新 200 行" :value="200" />
                <el-option label="最新 500 行" :value="500" />
                <el-option label="最新 1000 行" :value="1000" />
              </el-select>
            </div>

            <div class="toolbar-right">
              <el-button :icon="Refresh" circle size="default" @click="fetchAppLogs" :loading="loadingAppLogs" title="刷新" />
              <el-button :icon="Download" circle size="default" @click="handleDownload" :disabled="!currentFileName" title="下载日志文件" />
              <el-button :icon="Delete" circle size="default" @click="clearAppLogDisplay" title="清空显示" />
            </div>
          </div>
        </el-card>

        <el-card shadow="hover" class="mb-4" v-if="logFiles.length > 0">
          <template #header>
            <div class="flex justify-between items-center">
              <span>日志文件 ({{ logFiles.length }})</span>
              <el-button text size="small" @click="showFileList = !showFileList">
                {{ showFileList ? '收起' : '展开' }}
              </el-button>
            </div>
          </template>
          <div v-if="showFileList">
            <el-table :data="logFiles" size="small" stripe>
              <el-table-column prop="name" label="文件名" />
              <el-table-column label="大小" width="120">
                <template #default="{ row }">{{ formatSize(row.size) }}</template>
              </el-table-column>
              <el-table-column prop="modified" label="最后修改" width="180" />
              <el-table-column label="操作" width="100">
                <template #default="{ row }">
                  <el-button text size="small" type="primary" @click="viewFile(row.name)">查看</el-button>
                </template>
              </el-table-column>
            </el-table>
          </div>
        </el-card>

        <el-card shadow="hover">
          <template #header>
            <div class="flex justify-between items-center">
              <span>
                日志内容
                <el-tag size="small" type="info" class="ml-2" v-if="appLogLines.length">{{ appLogLines.length }} 行</el-tag>
              </span>
              <el-switch v-model="autoScroll" active-text="自动滚动" inactive-text="" size="small" />
            </div>
          </template>

          <el-skeleton v-if="loadingAppLogs" :rows="12" animated />

          <div v-else-if="appLogLines.length > 0" class="logs-container app-logs-container" ref="appLogsContainerRef">
            <div v-for="(line, idx) in appLogLines" :key="idx" :class="['log-line', getLineClass(line)]">
              <span class="line-no">{{ idx + 1 }}</span>
              <span class="line-content">{{ line }}</span>
            </div>
          </div>

          <el-empty v-else description="暂无日志数据" />
        </el-card>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { Refresh, RefreshRight, VideoPlay, VideoPause, Delete, Download, Search } from '@element-plus/icons-vue'
import { getDockerStatus, restartDocker, getDockerLogs, getLogFiles, getLogContent, getLogDownloadUrl } from '@/api'
import type { LogFile } from '@/api'
import type { DockerStatus } from '@/types/api'
import { formatDate } from '@/utils/formatters'
import { buildWsUrl } from '@/utils/websocket'

type ManagementTab = 'docker' | 'app-logs'

const props = defineProps<{
  modelValue: ManagementTab
}>()

const emit = defineEmits<{
  'update:modelValue': [value: ManagementTab]
}>()

const activeTabModel = computed({
  get: () => props.modelValue,
  set: (value: ManagementTab) => {
    emit('update:modelValue', value)
  },
})

const dockerStatus = ref<DockerStatus | null>(null)
const dockerLogs = ref<string>('')
const loadingStatus = ref(false)
const loadingDockerLogs = ref(false)
const restarting = ref(false)
const restartMessage = ref('')
const restartSuccess = ref(false)
const dockerLogLines = ref(100)
const wsConnected = ref(false)
const connecting = ref(false)
const ws = ref<WebSocket | null>(null)
const dockerLogsContainerRef = ref<HTMLElement | null>(null)

const logFiles = ref<LogFile[]>([])
const appLogLines = ref<string[]>([])
const loadingAppLogs = ref(false)
const showFileList = ref(false)
const autoScroll = ref(true)
const appLogsContainerRef = ref<HTMLElement | null>(null)
const selectedFile = ref<string>('')
const levelFilter = ref<string>('')
const keyword = ref<string>('')
const tailCount = ref<number>(200)
const currentFileName = ref<string>('')

function fetchDockerStatus() {
  loadingStatus.value = true
  getDockerStatus()
    .then((data) => {
      dockerStatus.value = data
    })
    .catch((err) => {
      console.error('获取Docker状态失败:', err)
      ElMessage.error('获取Docker状态失败')
    })
    .finally(() => {
      loadingStatus.value = false
    })
}

function stopLogStream() {
  if (ws.value) {
    ws.value.close()
    ws.value = null
  }
  wsConnected.value = false
  connecting.value = false
}

function startLogStream() {
  if (ws.value) {
    stopLogStream()
  }

  connecting.value = true
  const url = buildWsUrl('/api/system/docker/logs/ws', { tail: String(dockerLogLines.value) })

  try {
    ws.value = new WebSocket(url)

    ws.value.onopen = () => {
      wsConnected.value = true
      connecting.value = false
      dockerLogs.value = ''
    }

    ws.value.onmessage = (event) => {
      try {
        const data = JSON.parse(event.data)

        if (data.type === 'history') {
          dockerLogs.value = data.logs || ''
        } else if (data.type === 'log' || data.type === 'line') {
          dockerLogs.value += (dockerLogs.value ? '\n' : '') + (data.line || '')
          nextTick(() => {
            if (dockerLogsContainerRef.value) {
              dockerLogsContainerRef.value.scrollTop = dockerLogsContainerRef.value.scrollHeight
            }
          })
        } else if (data.type === 'error') {
          ElMessage.error(data.message || '日志流错误')
        }
      } catch (err) {
        console.error('解析WebSocket消息失败:', err)
      }
    }

    ws.value.onerror = (error) => {
      console.error('WebSocket错误:', error)
      ElMessage.error('日志流连接错误')
      connecting.value = false
      wsConnected.value = false
    }

    ws.value.onclose = () => {
      wsConnected.value = false
      connecting.value = false
    }
  } catch (err) {
    console.error('建立WebSocket连接失败:', err)
    ElMessage.error('无法建立日志流连接')
    connecting.value = false
  }
}

function handleDockerLogLinesChange() {
  if (wsConnected.value) {
    startLogStream()
  } else {
    fetchDockerLogs()
  }
}

function fetchDockerLogs() {
  loadingDockerLogs.value = true
  getDockerLogs(dockerLogLines.value)
    .then((data) => {
      if (data.success && data.logs) {
        dockerLogs.value = data.logs
      } else {
        dockerLogs.value = ''
        ElMessage.warning(data.error || '无法获取日志')
      }
    })
    .catch((err) => {
      console.error('获取Docker日志失败:', err)
      ElMessage.error('获取Docker日志失败')
      dockerLogs.value = ''
    })
    .finally(() => {
      loadingDockerLogs.value = false
    })
}

function clearDockerLogs() {
  dockerLogs.value = ''
}

function formatSize(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(2)} MB`
}

function getLineClass(line: string): string {
  if (line.includes('| ERROR')) return 'log-error'
  if (line.includes('| WARNING')) return 'log-warn'
  if (line.includes('| DEBUG')) return 'log-debug'
  return ''
}

function scrollAppLogsToBottom() {
  if (!autoScroll.value) return
  nextTick(() => {
    if (appLogsContainerRef.value) {
      appLogsContainerRef.value.scrollTop = appLogsContainerRef.value.scrollHeight
    }
  })
}

async function fetchFileList() {
  try {
    const res = await getLogFiles()
    if (res.success) {
      logFiles.value = res.files
      if (res.files.length > 0 && !currentFileName.value) {
        currentFileName.value = res.files[0].name
      }
    }
  } catch (err: any) {
    console.error('获取日志文件列表失败:', err)
  }
}

async function fetchAppLogs() {
  loadingAppLogs.value = true
  try {
    const res = await getLogContent({
      file: selectedFile.value || undefined,
      tail: tailCount.value,
      level: levelFilter.value || undefined,
      keyword: keyword.value || undefined,
    })
    if (res.success) {
      appLogLines.value = res.lines
      currentFileName.value = selectedFile.value || (logFiles.value.length > 0 ? logFiles.value[0].name : '')
    } else {
      ElMessage.error(res.error || '获取日志失败')
    }
  } catch (err: any) {
    console.error('获取日志内容失败:', err)
    ElMessage.error('获取日志内容失败')
  } finally {
    loadingAppLogs.value = false
  }
}

function viewFile(name: string) {
  selectedFile.value = name
  void fetchAppLogs()
}

function handleDownload() {
  if (!currentFileName.value) return
  window.open(getLogDownloadUrl(currentFileName.value), '_blank')
}

function clearAppLogDisplay() {
  appLogLines.value = []
}

function handleRestart() {
  if (!dockerStatus.value?.in_docker) {
    ElMessage.warning('当前不在Docker容器内运行')
    return
  }

  void ElMessageBox.confirm(
    '确定要重启Docker容器吗？重启后服务会短暂中断。',
    '确认重启',
    {
      confirmButtonText: '确定重启',
      cancelButtonText: '取消',
      type: 'warning',
      dangerouslyUseHTMLString: false,
    },
  ).then(() => {
    restarting.value = true
    restartMessage.value = ''

    restartDocker()
      .then((data) => {
        if (data.success) {
          restartSuccess.value = true
          restartMessage.value = data.message || '容器重启成功'
          ElMessage.success(restartMessage.value)
          window.setTimeout(() => {
            fetchDockerStatus()
            fetchDockerLogs()
          }, 2000)
        } else {
          restartSuccess.value = false
          restartMessage.value = data.error || '重启失败'
          ElMessage.error(restartMessage.value)
        }
      })
      .catch((err) => {
        restartSuccess.value = false
        restartMessage.value = err.message || '重启操作失败'
        ElMessage.error(restartMessage.value)
        console.error('重启Docker容器失败:', err)
      })
      .finally(() => {
        restarting.value = false
      })
  }).catch(() => {
    // 用户取消
  })
}

function getStatusType(status?: string): 'success' | 'warning' | 'danger' | 'info' {
  if (!status) return 'info'
  const lowerStatus = status.toLowerCase()
  if (lowerStatus.includes('running') || lowerStatus.includes('up')) {
    return 'success'
  }
  if (lowerStatus.includes('restarting') || lowerStatus.includes('paused')) {
    return 'warning'
  }
  if (lowerStatus.includes('stopped') || lowerStatus.includes('exited')) {
    return 'danger'
  }
  return 'info'
}

watch(
  () => props.modelValue,
  (tab) => {
    if (tab !== 'docker') {
      stopLogStream()
    }

    if (tab === 'app-logs' && logFiles.value.length === 0 && !loadingAppLogs.value) {
      void fetchFileList().then(() => fetchAppLogs())
    }
  },
  { immediate: true },
)

watch(appLogLines, () => {
  scrollAppLogsToBottom()
})

onMounted(() => {
  fetchDockerStatus()
  fetchDockerLogs()
})

onUnmounted(() => {
  stopLogStream()
})
</script>

<style scoped>
.system-page {
  @apply space-y-4;
}

.control-actions {
  @apply space-y-4;
}

.system-tabs {
  @apply rounded-xl bg-white p-4;
}

.system-tabs:deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.system-tabs:deep(.el-tabs__nav-wrap::after) {
  background-color: rgba(226, 232, 240, 0.9);
}

.toolbar {
  @apply flex flex-wrap justify-between items-center gap-3;
}

.toolbar-left {
  @apply flex flex-wrap items-center gap-2;
}

.toolbar-right {
  @apply flex items-center gap-1;
}

.logs-container {
  @apply bg-gray-900 rounded-lg p-4 overflow-auto;
  max-height: 600px;
  font-family: 'Courier New', monospace;
  position: relative;
}

.app-logs-container {
  @apply p-0;
  max-height: 65vh;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.6;
}

.logs-content {
  @apply text-gray-100 text-sm whitespace-pre-wrap;
  margin: 0;
  line-height: 1.5;
  word-break: break-all;
}

.log-line {
  @apply flex px-3 py-0;
  border-bottom: 1px solid rgba(255, 255, 255, 0.03);
  transition: background-color 0.15s;
}

.log-line:hover {
  background-color: rgba(255, 255, 255, 0.05);
}

.log-error {
  background-color: rgba(239, 68, 68, 0.12);
}

.log-warn {
  background-color: rgba(245, 158, 11, 0.10);
}

.log-debug {
  @apply text-gray-500;
}

.line-no {
  @apply text-gray-600 select-none pr-3 text-right flex-shrink-0;
  min-width: 40px;
  border-right: 1px solid rgba(255, 255, 255, 0.06);
  margin-right: 12px;
}

.line-content {
  @apply text-gray-200 whitespace-pre-wrap break-all;
}

.log-error .line-content {
  @apply text-red-400;
}

.log-warn .line-content {
  @apply text-yellow-400;
}

.logs-container::-webkit-scrollbar {
  width: 8px;
}

.logs-container::-webkit-scrollbar-track {
  @apply bg-gray-800 rounded;
}

.logs-container::-webkit-scrollbar-thumb {
  @apply bg-gray-600 rounded;
}

.logs-container::-webkit-scrollbar-thumb:hover {
  @apply bg-gray-500;
}

:deep(.el-descriptions__label) {
  @apply font-medium;
}
</style>
