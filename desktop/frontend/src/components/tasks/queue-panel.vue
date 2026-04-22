<template>
  <el-card v-loading="isLoading" shadow="hover" class="queue-panel-shell">
    <div class="page-toolbar">
      <div class="page-title">{{ title }}</div>
      <div class="page-actions">
        <el-button @click="fetchQueue" :icon="Refresh">刷新</el-button>
        <el-button :type="autoRefresh ? 'primary' : 'default'" @click="autoRefresh = !autoRefresh">
          {{ autoRefresh ? '自动刷新中' : '开启自动刷新' }}
        </el-button>
      </div>
    </div>

    <div class="stats-row">
      <div class="stat-item">
        <span class="stat-item-value">{{ queueSize }}</span>
        <span class="stat-item-label">队列总数</span>
      </div>
      <div class="stat-item is-active">
        <span class="stat-item-value">{{ currentProcessing ? 1 : 0 }}</span>
        <span class="stat-item-label">处理中</span>
      </div>
      <div class="stat-item is-warning">
        <span class="stat-item-value">{{ waitingItems.length }}</span>
        <span class="stat-item-label">等待中</span>
      </div>
      <div class="stat-item" :class="queueData?.flood_wait?.is_waiting ? 'is-danger' : 'is-success'">
        <span class="stat-item-value">
          {{ queueData?.flood_wait?.is_waiting ? queueData.flood_wait.remaining_seconds : 0 }}
        </span>
        <span class="stat-item-label">限流剩余秒数</span>
      </div>
    </div>

    <div class="panel-toolbar">
      <el-input
        v-model="keyword"
        clearable
        placeholder="搜索标题、任务类型"
        class="toolbar-search"
      />
      <el-select v-model="typeFilter" class="toolbar-filter">
        <el-option label="全部类型" value="all" />
        <el-option label="媒体组" value="media_group" />
        <el-option label="单个文件" value="single" />
      </el-select>
      <div class="toolbar-meta">
        匹配 {{ filteredWaitingItems.length }} / {{ waitingItems.length }} 个等待项
      </div>
    </div>

    <el-alert
      v-if="queueData?.flood_wait?.is_waiting"
      type="warning"
      :closable="false"
      show-icon
      class="flood-wait-alert"
    >
      <template #title>
        <strong>Telegram 限流中</strong>
      </template>
      <div class="flood-wait-info">
        <p>限流时长: {{ queueData.flood_wait.wait_seconds }} 秒</p>
        <p>剩余时间: {{ queueData.flood_wait.remaining_seconds }} 秒</p>
        <p class="flood-wait-message">所有消息已进入等待队列，限流结束后会自动恢复。</p>
      </div>
    </el-alert>

    <el-alert
      v-if="error"
      :title="error"
      type="error"
      :closable="false"
      class="panel-error"
    />

    <div class="queue-section">
      <div class="section-header">
        <h3>正在处理</h3>
      </div>
      <el-empty
        v-if="!filteredCurrentProcessing"
        :description="keyword || typeFilter !== 'all' ? '当前筛选条件下没有处理中的任务' : '当前没有正在处理的任务'"
        :image-size="80"
      />
      <el-card v-else shadow="never" class="processing-card">
        <div class="processing-info">
          <el-tag type="primary" size="large">处理中</el-tag>
          <div class="processing-details">
            <p><strong>标题:</strong> {{ filteredCurrentProcessing.title }}</p>
            <p><strong>类型:</strong> {{ filteredCurrentProcessing.type === 'media_group' ? '媒体组' : '单个文件' }}</p>
            <p v-if="filteredCurrentProcessing.media_group_total">
              <strong>文件数:</strong> {{ filteredCurrentProcessing.media_group_total }}
            </p>
            <p v-if="filteredCurrentProcessing.task_gids && filteredCurrentProcessing.task_gids.length">
              <strong>下载任务:</strong> {{ filteredCurrentProcessing.task_gids.length }} 个
            </p>
          </div>
        </div>
      </el-card>
    </div>

    <el-divider />

    <div class="queue-section">
      <div class="section-header">
        <h3>等待队列</h3>
        <span class="section-meta">{{ filteredWaitingItems.length }} 个</span>
      </div>
      <el-empty
        v-if="filteredWaitingItems.length === 0"
        :description="keyword || typeFilter !== 'all' ? '当前筛选条件下没有等待任务' : '队列为空'"
        :image-size="80"
      />
      <el-timeline v-else>
        <el-timeline-item
          v-for="(item, index) in filteredWaitingItems"
          :key="item.queue_id"
          :timestamp="`位置 ${index + 1}`"
          placement="top"
        >
          <el-card shadow="never" class="queue-item-card">
            <div class="queue-item-info">
              <el-tag :type="item.type === 'media_group' ? 'warning' : 'info'" size="small">
                {{ item.type === 'media_group' ? '媒体组' : '单个文件' }}
              </el-tag>
              <p class="item-title">{{ item.title }}</p>
              <p v-if="item.media_group_total" class="item-detail">
                包含 {{ item.media_group_total }} 个文件
              </p>
            </div>
          </el-card>
        </el-timeline-item>
      </el-timeline>
    </div>
  </el-card>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import { Refresh } from '@element-plus/icons-vue'
import { useIntervalFn } from '@vueuse/core'
import { getQueue, type QueueStatus } from '@/api'

interface QueueItem {
  queue_id: string | number
  title?: string
  type?: 'media_group' | 'single'
  media_group_total?: number
  task_gids?: string[]
}

withDefaults(defineProps<{
  title?: string
}>(), {
  title: '任务队列',
})

const autoRefresh = ref(true)
const queueData = ref<QueueStatus | null>(null)
const isLoading = ref(false)
const error = ref('')
const keyword = ref('')
const typeFilter = ref<'all' | 'media_group' | 'single'>('all')

const currentProcessing = computed<QueueItem | null>(() => (queueData.value?.current_processing as QueueItem | null) || null)
const waitingItems = computed<QueueItem[]>(() => (queueData.value?.waiting_items as QueueItem[]) || [])
const queueSize = computed(() => queueData.value?.queue_size || 0)

function normalizeQueueText(value: unknown): string {
  return String(value || '').toLowerCase()
}

function matchesQueueItem(item: QueueItem | null): boolean {
  if (!item) return false

  if (typeFilter.value !== 'all' && item.type !== typeFilter.value) {
    return false
  }

  const query = keyword.value.trim().toLowerCase()
  if (!query) return true

  return [
    item.title,
    item.type === 'media_group' ? '媒体组' : '单个文件',
  ].some((field) => normalizeQueueText(field).includes(query))
}

const filteredCurrentProcessing = computed(() => {
  return matchesQueueItem(currentProcessing.value) ? currentProcessing.value : null
})

const filteredWaitingItems = computed(() => {
  return waitingItems.value.filter(item => matchesQueueItem(item))
})

function fetchQueue() {
  isLoading.value = true
  error.value = ''

  getQueue()
    .then(data => {
      if (data.success) {
        queueData.value = data
      } else {
        error.value = data.error || '获取队列状态失败'
      }
    })
    .catch(err => {
      error.value = err.message || '获取队列状态失败'
    })
    .finally(() => {
      isLoading.value = false
    })
}

const { pause, resume } = useIntervalFn(fetchQueue, 3000, { immediate: false })

watch(autoRefresh, (enabled) => {
  if (enabled) {
    resume()
  } else {
    pause()
  }
})

onMounted(() => {
  fetchQueue()
  if (autoRefresh.value) {
    resume()
  }
})

onUnmounted(() => {
  pause()
})
</script>

<style scoped>
.queue-panel-shell {
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

.stat-item.is-warning .stat-item-value {
  color: #d97706;
}

.stat-item.is-success .stat-item-value {
  color: #059669;
}

.stat-item.is-danger .stat-item-value {
  color: #dc2626;
}

.panel-toolbar {
  @apply mb-5 flex flex-col gap-3 lg:flex-row lg:items-center;
}

.toolbar-search {
  @apply lg:max-w-sm;
}

.toolbar-filter {
  @apply lg:w-44;
}

.toolbar-meta {
  @apply text-sm text-slate-500 lg:ml-auto;
}

.panel-error,
.flood-wait-alert {
  @apply mb-5;
}

.flood-wait-info {
  @apply mt-2 space-y-1;
}

.flood-wait-message {
  @apply text-sm text-slate-600;
}

.queue-section {
  @apply space-y-4;
}

.section-header {
  @apply flex items-center justify-between gap-3;
}

.section-header h3 {
  @apply text-lg font-semibold text-slate-800;
}

.section-meta {
  @apply text-sm text-slate-500;
}

.processing-card {
  @apply border border-blue-200 bg-blue-50;
}

.processing-info {
  @apply flex items-start gap-4;
}

.processing-details {
  @apply flex-1;
}

.processing-details p {
  @apply mb-2 text-slate-700 last:mb-0;
}

.queue-item-card {
  @apply border border-slate-200 bg-slate-50;
}

.queue-item-info {
  @apply space-y-2;
}

.item-title {
  @apply font-semibold text-slate-800;
}

.item-detail {
  @apply text-sm text-slate-600;
}

:deep(.el-timeline-item__timestamp) {
  @apply font-semibold text-blue-600;
}
</style>
