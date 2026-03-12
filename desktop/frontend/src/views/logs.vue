<template>
  <div class="logs-page">
    <!-- 工具栏 -->
    <el-card shadow="hover" class="mb-4">
      <div class="toolbar">
        <div class="toolbar-left">
          <el-select v-model="selectedFile" placeholder="当前日志" clearable style="width: 220px" size="default" @change="fetchLogs">
            <el-option v-for="f in logFiles" :key="f.name" :label="`${f.name} (${formatSize(f.size)})`" :value="f.name" />
          </el-select>

          <el-select v-model="levelFilter" placeholder="全部级别" clearable style="width: 130px" size="default" @change="fetchLogs">
            <el-option label="ERROR" value="ERROR" />
            <el-option label="WARNING" value="WARNING" />
            <el-option label="INFO" value="INFO" />
            <el-option label="DEBUG" value="DEBUG" />
          </el-select>

          <el-input v-model="keyword" placeholder="关键词搜索" clearable style="width: 200px" size="default" @keyup.enter="fetchLogs" @clear="fetchLogs">
            <template #prefix>
              <el-icon><Search /></el-icon>
            </template>
          </el-input>

          <el-select v-model="tailCount" style="width: 120px" size="default" @change="fetchLogs">
            <el-option label="最新 100 行" :value="100" />
            <el-option label="最新 200 行" :value="200" />
            <el-option label="最新 500 行" :value="500" />
            <el-option label="最新 1000 行" :value="1000" />
          </el-select>
        </div>

        <div class="toolbar-right">
          <el-button :icon="Refresh" circle size="default" @click="fetchLogs" :loading="loading" title="刷新" />
          <el-button :icon="Download" circle size="default" @click="handleDownload" :disabled="!currentFileName" title="下载日志文件" />
          <el-button :icon="Delete" circle size="default" @click="clearDisplay" title="清空显示" />
        </div>
      </div>
    </el-card>

    <!-- 日志文件信息 -->
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

    <!-- 日志内容 -->
    <el-card shadow="hover">
      <template #header>
        <div class="flex justify-between items-center">
          <span>
            日志内容
            <el-tag size="small" type="info" class="ml-2" v-if="logLines.length">{{ logLines.length }} 行</el-tag>
          </span>
          <el-switch v-model="autoScroll" active-text="自动滚动" inactive-text="" size="small" />
        </div>
      </template>

      <el-skeleton v-if="loading" :rows="12" animated />

      <div v-else-if="logLines.length > 0" class="logs-container" ref="logsContainerRef">
        <div v-for="(line, idx) in logLines" :key="idx" :class="['log-line', getLineClass(line)]">
          <span class="line-no">{{ idx + 1 }}</span>
          <span class="line-content">{{ line }}</span>
        </div>
      </div>

      <el-empty v-else description="暂无日志数据" />
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, nextTick, watch } from 'vue'
import { ElMessage } from 'element-plus'
import { Refresh, Download, Delete, Search } from '@element-plus/icons-vue'
import { getLogFiles, getLogContent, getLogDownloadUrl } from '@/api'
import type { LogFile } from '@/api'

const logFiles = ref<LogFile[]>([])
const logLines = ref<string[]>([])
const loading = ref(false)
const showFileList = ref(false)
const autoScroll = ref(true)
const logsContainerRef = ref<HTMLElement | null>(null)

const selectedFile = ref<string>('')
const levelFilter = ref<string>('')
const keyword = ref<string>('')
const tailCount = ref<number>(200)

const currentFileName = ref<string>('')

function formatSize(bytes: number): string {
  if (bytes < 1024) return bytes + ' B'
  if (bytes < 1024 * 1024) return (bytes / 1024).toFixed(1) + ' KB'
  return (bytes / (1024 * 1024)).toFixed(2) + ' MB'
}

function getLineClass(line: string): string {
  if (line.includes('| ERROR')) return 'log-error'
  if (line.includes('| WARNING')) return 'log-warn'
  if (line.includes('| DEBUG')) return 'log-debug'
  return ''
}

function scrollToBottom() {
  if (!autoScroll.value) return
  nextTick(() => {
    if (logsContainerRef.value) {
      logsContainerRef.value.scrollTop = logsContainerRef.value.scrollHeight
    }
  })
}

watch(logLines, () => scrollToBottom())

async function fetchFileList() {
  try {
    const res = await getLogFiles()
    if (res.success) {
      logFiles.value = res.files
      if (res.files.length > 0) {
        currentFileName.value = res.files[0].name
      }
    }
  } catch (e: any) {
    console.error('获取日志文件列表失败:', e)
  }
}

async function fetchLogs() {
  loading.value = true
  try {
    const res = await getLogContent({
      file: selectedFile.value || undefined,
      tail: tailCount.value,
      level: levelFilter.value || undefined,
      keyword: keyword.value || undefined,
    })
    if (res.success) {
      logLines.value = res.lines
      currentFileName.value = selectedFile.value || (logFiles.value.length > 0 ? logFiles.value[0].name : '')
    } else {
      ElMessage.error(res.error || '获取日志失败')
    }
  } catch (e: any) {
    console.error('获取日志内容失败:', e)
    ElMessage.error('获取日志内容失败')
  } finally {
    loading.value = false
  }
}

function viewFile(name: string) {
  selectedFile.value = name
  fetchLogs()
}

function handleDownload() {
  if (!currentFileName.value) return
  window.open(getLogDownloadUrl(currentFileName.value), '_blank')
}

function clearDisplay() {
  logLines.value = []
}

onMounted(async () => {
  await fetchFileList()
  await fetchLogs()
})
</script>

<style scoped>
.logs-page {
  @apply space-y-4;
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
  @apply bg-gray-900 rounded-lg overflow-auto;
  max-height: 65vh;
  font-family: 'JetBrains Mono', 'Fira Code', 'Courier New', monospace;
  font-size: 12.5px;
  line-height: 1.6;
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
</style>
