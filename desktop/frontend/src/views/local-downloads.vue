<template>
  <div class="local-downloads-page">
    <el-card shadow="hover" class="local-downloads-shell">
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
          <span class="stat-item-label">失败</span>
        </div>
      </div>

      <el-empty
        v-if="desktopDownloadList.length === 0"
        description='还没有本地下载任务，请到"我的网盘"里选择文件下载。'
        :image-size="80"
      />

      <el-table
        v-else
        :data="desktopDownloadList"
        stripe
        size="small"
        style="width: 100%"
        row-key="transferId"
      >
        <el-table-column prop="fileName" label="文件名" min-width="260" show-overflow-tooltip>
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

        <el-table-column prop="localPath" label="保存位置" min-width="240" show-overflow-tooltip>
          <template #default="{ row }">
            <span class="path-text">{{ row.localPath }}</span>
          </template>
        </el-table-column>

        <el-table-column label="错误" min-width="180" show-overflow-tooltip>
          <template #default="{ row }">
            <span v-if="row.error" class="error-text">{{ row.error }}</span>
            <span v-else class="no-error">-</span>
          </template>
        </el-table-column>
      </el-table>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { Document } from '@element-plus/icons-vue'
import { useDesktopDownloads } from '@/composables/useDesktopDownloads'

const {
  desktopDownloadList,
  desktopDownloadStats,
  getDesktopDownloadLabel,
  getDesktopDownloadTagType,
  getDesktopDownloadProgressStatus,
  formatDesktopDownloadMeta,
} = useDesktopDownloads()
</script>

<style scoped>
.local-downloads-page {
  @apply space-y-8;
  animation: fadeIn 0.5s ease-out;
}

.local-downloads-page :deep(.el-card) {
  border-radius: 16px;
  border: 1px solid rgba(229, 231, 235, 0.8);
  transition: all 0.3s ease;
  overflow: hidden;
}

.local-downloads-page :deep(.el-card:hover) {
  box-shadow: 0 8px 16px rgba(0, 0, 0, 0.08);
  border-color: rgba(102, 126, 234, 0.2);
}

.stats-row {
  @apply flex items-center gap-6 mb-5 pb-5;
  border-bottom: 1px solid rgba(229, 231, 235, 0.8);
}

.stat-item {
  @apply flex items-center gap-2;
}

.stat-item-value {
  @apply text-2xl font-bold text-gray-900;
}

.stat-item-label {
  @apply text-sm text-gray-500 font-medium;
}

.stat-item.is-active .stat-item-value {
  color: #667eea;
}

.stat-item.is-success .stat-item-value {
  color: #10b981;
}

.stat-item.is-danger .stat-item-value {
  color: #ef4444;
}

.file-info {
  @apply flex items-center gap-2;
}

.file-icon {
  color: #667eea;
  transition: all 0.2s ease;
}

.local-downloads-page :deep(.el-table__row:hover) .file-icon {
  transform: scale(1.1);
}

.size-text {
  @apply text-sm text-gray-700 font-semibold;
}

.path-text {
  font-family: 'Monaco', 'Menlo', 'Ubuntu Mono', monospace;
  font-size: 12px;
  color: #6b7280;
  word-break: break-all;
}

.error-text {
  @apply text-sm text-red-500;
}

.no-error {
  @apply text-gray-400;
}

/* table */
.local-downloads-page :deep(.el-table) {
  border-radius: 8px;
  overflow: hidden;
}

.local-downloads-page :deep(.el-table__row) {
  transition: all 0.2s ease;
}

.local-downloads-page :deep(.el-table__row:hover) {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.05), rgba(118, 75, 162, 0.03));
}

/* progress */
:deep(.el-progress__text) {
  @apply font-semibold;
}

:deep(.el-progress-bar__outer) {
  border-radius: 10px;
  overflow: hidden;
}

:deep(.el-progress-bar__inner) {
  border-radius: 10px;
  transition: all 0.3s ease;
}

/* tag */
:deep(.el-tag) {
  border-radius: 6px;
  font-weight: 500;
}

@keyframes fadeIn {
  from { opacity: 0; transform: translateY(10px); }
  to { opacity: 1; transform: translateY(0); }
}
</style>
