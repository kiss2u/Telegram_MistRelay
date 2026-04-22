<template>
  <el-card shadow="hover" class="local-downloads-shell">
    <div class="page-toolbar">
      <div class="page-title">{{ title }}</div>
      <div v-if="showDriveButton" class="page-actions">
        <el-button @click="router.push('/drive')">前往 tg 网盘</el-button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-item">
        <span class="stat-item-value">{{ desktopDownloadStats.total }}</span>
        <span class="stat-item-label">总任务</span>
      </div>
      <div class="stat-item is-active">
        <span class="stat-item-value">{{ desktopDownloadStats.active }}</span>
        <span class="stat-item-label">进行中</span>
      </div>
      <div class="stat-item is-success">
        <span class="stat-item-value">{{ desktopDownloadStats.completed }}</span>
        <span class="stat-item-label">已完成</span>
      </div>
      <div class="stat-item is-danger">
        <span class="stat-item-value">{{ desktopDownloadStats.failed }}</span>
        <span class="stat-item-label">失败/取消</span>
      </div>
    </div>

    <div class="panel-toolbar">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索文件名、保存位置、错误信息"
        class="toolbar-search"
      />
      <el-select v-model="statusFilter" class="toolbar-filter">
        <el-option label="全部状态" value="all" />
        <el-option label="进行中" value="active" />
        <el-option label="已完成" value="completed" />
        <el-option label="失败/取消" value="failed" />
      </el-select>
      <div class="toolbar-meta">
        匹配 {{ filteredDesktopDownloadList.length }} / {{ desktopDownloadList.length }} 项
      </div>
      <div class="page-actions">
        <el-button @click="clearDesktopDownloads('completed')" :disabled="desktopDownloadStats.completed === 0">
          清空已完成
        </el-button>
        <el-button @click="clearDesktopDownloads('failed')" :disabled="desktopDownloadStats.failed === 0">
          清空失败/取消
        </el-button>
        <el-button
          type="danger"
          plain
          @click="clearDesktopDownloads('all')"
          :disabled="desktopDownloadStats.total === 0"
        >
          清空全部
        </el-button>
      </div>
    </div>

    <el-empty
      v-if="filteredDesktopDownloadList.length === 0"
      :description="desktopDownloadList.length === 0 ? '还没有本地下载任务，请到 tg 网盘里选择文件下载。' : '当前筛选条件下没有匹配任务。'"
      :image-size="80"
    />

    <el-table
      v-else
      :data="filteredDesktopDownloadList"
      stripe
      size="small"
      style="width: 100%"
      row-key="transferId"
    >
      <el-table-column prop="fileName" label="文件名" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          <div class="file-info">
            <el-icon class="file-icon"><Document /></el-icon>
            <span>{{ row.fileName }}</span>
          </div>
        </template>
      </el-table-column>

      <el-table-column label="状态" width="100">
        <template #default="{ row }">
          <el-tag :type="getDesktopDownloadTagType(row)" size="small">
            {{ getDesktopDownloadLabel(row) }}
          </el-tag>
        </template>
      </el-table-column>

      <el-table-column label="进度" width="180">
        <template #default="{ row }">
          <el-progress
            :percentage="row.progressPercent"
            :status="getDesktopDownloadProgressStatus(row)"
            :indeterminate="!row.totalBytes && row.state !== 'completed' && row.state !== 'error'"
            :stroke-width="6"
          />
        </template>
      </el-table-column>

      <el-table-column label="大小" width="180">
        <template #default="{ row }">
          <span class="size-text">{{ formatDesktopDownloadMeta(row) }}</span>
        </template>
      </el-table-column>

      <el-table-column label="速度" width="120">
        <template #default="{ row }">
          <span class="speed-text">{{ formatDesktopDownloadSpeed(row) }}</span>
        </template>
      </el-table-column>

      <el-table-column prop="localPath" label="保存位置" min-width="240" show-overflow-tooltip>
        <template #default="{ row }">
          <span class="path-text">{{ row.localPath }}</span>
        </template>
      </el-table-column>

      <el-table-column label="操作" width="320" fixed="right">
        <template #default="{ row }">
          <div class="row-actions">
            <el-button
              v-if="canCancelDesktopDownload(row)"
              link
              type="warning"
              @click="cancelDesktopDownloadTask(row.transferId)"
            >
              取消
            </el-button>
            <el-button
              v-if="canRetryDesktopDownload(row)"
              link
              type="primary"
              @click="retryDesktopDownloadTask(row.transferId)"
            >
              重试
            </el-button>
            <el-button
              v-if="canOpenDesktopDownload(row)"
              link
              type="primary"
              @click="openDesktopDownloadFile(row.localPath)"
            >
              打开文件
            </el-button>
            <el-button
              v-if="canOpenDesktopDownload(row)"
              link
              @click="showDesktopDownloadInFolder(row.localPath)"
            >
              打开目录
            </el-button>
            <el-button link type="primary" @click="showTaskDetails(row)">查看详情</el-button>
            <el-button
              link
              type="danger"
              :disabled="!isDesktopDownloadTerminal(row)"
              @click="removeDesktopDownload(row.transferId)"
            >
              删除
            </el-button>
          </div>
        </template>
      </el-table-column>
    </el-table>
  </el-card>

  <el-dialog v-model="detailVisible" title="任务详情" width="680px">
    <el-descriptions v-if="selectedTask" :column="1" border>
      <el-descriptions-item label="文件名">{{ selectedTask.fileName }}</el-descriptions-item>
      <el-descriptions-item label="状态">
        <el-tag :type="getDesktopDownloadTagType(selectedTask)" size="small">
          {{ getDesktopDownloadLabel(selectedTask) }}
        </el-tag>
      </el-descriptions-item>
      <el-descriptions-item label="进度">{{ selectedTask.progressPercent }}%</el-descriptions-item>
      <el-descriptions-item label="大小">{{ formatDesktopDownloadMeta(selectedTask) }}</el-descriptions-item>
      <el-descriptions-item label="下载速度">{{ formatDesktopDownloadSpeed(selectedTask) }}</el-descriptions-item>
      <el-descriptions-item label="保存位置">{{ selectedTask.localPath }}</el-descriptions-item>
      <el-descriptions-item label="错误信息">
        {{ selectedTask.error || '-' }}
      </el-descriptions-item>
      <el-descriptions-item label="传输 ID">{{ selectedTask.transferId }}</el-descriptions-item>
    </el-descriptions>
    <template #footer>
      <div v-if="selectedTask" class="dialog-actions">
        <el-button
          v-if="canCancelDesktopDownload(selectedTask)"
          type="warning"
          plain
          @click="cancelDesktopDownloadTask(selectedTask.transferId)"
        >
          取消下载
        </el-button>
        <el-button
          v-if="canRetryDesktopDownload(selectedTask)"
          type="primary"
          plain
          @click="retryDesktopDownloadTask(selectedTask.transferId)"
        >
          重试下载
        </el-button>
        <el-button
          v-if="canOpenDesktopDownload(selectedTask)"
          @click="openDesktopDownloadFile(selectedTask.localPath)"
        >
          打开文件
        </el-button>
        <el-button
          v-if="canOpenDesktopDownload(selectedTask)"
          @click="showDesktopDownloadInFolder(selectedTask.localPath)"
        >
          打开目录
        </el-button>
        <el-button @click="detailVisible = false">关闭</el-button>
      </div>
    </template>
  </el-dialog>
</template>

<script setup lang="ts">
import { computed, ref } from 'vue'
import { useRouter } from 'vue-router'
import { Document } from '@element-plus/icons-vue'
import { useDesktopDownloads } from '@/composables/useDesktopDownloads'
import type { DesktopTransferStatus } from '@/utils/desktop'

withDefaults(defineProps<{
  title?: string
  showDriveButton?: boolean
}>(), {
  title: '本地下载任务',
  showDriveButton: true,
})

const router = useRouter()
const detailVisible = ref(false)
const selectedTask = ref<DesktopTransferStatus | null>(null)
const keyword = ref('')
const statusFilter = ref<'all' | 'active' | 'completed' | 'failed'>('all')

const {
  desktopDownloadList,
  desktopDownloadStats,
  isDesktopDownloadTerminal,
  canCancelDesktopDownload,
  canRetryDesktopDownload,
  canOpenDesktopDownload,
  getDesktopDownloadLabel,
  getDesktopDownloadTagType,
  getDesktopDownloadProgressStatus,
  formatDesktopDownloadMeta,
  formatDesktopDownloadSpeed,
  cancelDesktopDownloadTask,
  retryDesktopDownloadTask,
  openDesktopDownloadFile,
  showDesktopDownloadInFolder,
  removeDesktopDownload,
  clearDesktopDownloads,
} = useDesktopDownloads()

function matchesStatusFilter(task: DesktopTransferStatus): boolean {
  if (statusFilter.value === 'all') return true
  if (statusFilter.value === 'completed') return task.state === 'completed'
  if (statusFilter.value === 'failed') return task.state === 'error' || task.state === 'cancelled'
  return task.state === 'pending' || task.state === 'downloading' || task.state === 'cancelling'
}

const filteredDesktopDownloadList = computed(() => {
  const query = keyword.value.trim().toLowerCase()

  return desktopDownloadList.value.filter((task) => {
    if (!matchesStatusFilter(task)) return false

    if (!query) return true

    return [
      task.fileName,
      task.localPath,
      task.error,
      getDesktopDownloadLabel(task),
    ].some((value) => String(value || '').toLowerCase().includes(query))
  })
})

function showTaskDetails(task: DesktopTransferStatus) {
  selectedTask.value = task
  detailVisible.value = true
}
</script>

<style scoped>
.local-downloads-shell {
  @apply rounded-2xl;
}

.page-toolbar {
  @apply mb-6 flex flex-col gap-4 border-b border-slate-100 pb-4 lg:flex-row lg:items-center lg:justify-between;
}

.page-title {
  @apply text-lg font-semibold text-slate-900;
}

.page-actions {
  @apply flex flex-wrap items-center gap-3;
}

.stats-row {
  @apply mb-5 flex flex-wrap items-center gap-6;
}

.panel-toolbar {
  @apply flex flex-wrap items-center gap-6;
}

.stat-item {
  @apply flex items-center gap-2;
}

.stat-item-value {
  @apply text-2xl font-bold text-slate-900;
}

.stat-item-label {
  @apply text-sm font-medium text-slate-500;
}

.stat-item.is-active .stat-item-value {
  color: #2563eb;
}

.stat-item.is-success .stat-item-value {
  color: #059669;
}

.stat-item.is-danger .stat-item-value {
  color: #dc2626;
}

.toolbar-search {
  @apply lg:max-w-sm;
}

.toolbar-filter {
  @apply lg:w-44;
}

.toolbar-meta {
  @apply text-sm text-slate-500;
}

.file-info {
  @apply flex items-center gap-2;
}

.file-icon {
  color: #2563eb;
}

.row-actions {
  @apply flex flex-wrap items-center gap-3;
}

.size-text {
  @apply text-sm font-semibold text-slate-700;
}

.speed-text {
  @apply text-sm font-semibold text-sky-600;
}

.path-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  color: #64748b;
  word-break: break-all;
}

.dialog-actions {
  @apply flex flex-wrap justify-end gap-3;
}
</style>
