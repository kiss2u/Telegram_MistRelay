<template>
  <div class="drive-page" v-loading="previewLoading">
    <el-card shadow="hover">
      <template #header>
        <div class="drive-header">
          <div v-if="availableRemotes.length > 0" class="drive-header-tools">
            <el-select
              v-model="currentRemote"
              @change="handleRemoteChange"
              placeholder="选择云存储"
              class="header-remote-select"
              popper-class="drive-remote-popper"
              fit-input-width
            >
              <el-option
                v-for="remote in availableRemotes"
                :key="remote.name"
                :label="remote.name === TELEGRAM_REMOTE_NAME ? 'Telegram 频道' : remote.name"
                :value="remote.name"
              >
                <div class="remote-option">
                  <div class="remote-option-head">
                    <span class="remote-option-name">{{ remote.name === TELEGRAM_REMOTE_NAME ? 'Telegram 频道' : remote.name }}</span>
                    <el-tag size="small" effect="plain" round>{{ remote.type }}</el-tag>
                  </div>
                  <div class="remote-option-meta">
                    <template v-if="remote.name === TELEGRAM_REMOTE_NAME">
                      <span>{{ telegramUsage ? formatBytes(telegramUsage.total_size) + ' · ' + telegramUsage.total_count + ' 个文件' : '加载中...' }}</span>
                    </template>
                    <template v-else>
                      <span>{{ getRemoteUsageSummary(remote.name) }}</span>
                      <span v-if="getRemoteUsagePercent(remote.name) !== null" class="remote-option-percent">
                        {{ getRemoteUsagePercent(remote.name)!.toFixed(0) }}%
                      </span>
                    </template>
                  </div>
                </div>
              </el-option>
            </el-select>

            <div v-if="currentRemote" class="header-usage">
              <template v-if="isTelegramMode">
                <template v-if="loadingTelegramUsage">
                  <span class="header-usage-text">容量读取中...</span>
                </template>
                <template v-else-if="telegramUsage">
                  <span class="header-usage-name">Telegram 频道</span>
                  <span class="header-usage-text">{{ formatBytes(telegramUsage.total_size) }} · {{ telegramUsage.total_count }} 个文件</span>
                  <el-tag size="small" round effect="plain">
                    {{ telegramUsage.videos }} 视频 · {{ telegramUsage.images }} 图片
                  </el-tag>
                </template>
                <el-button :icon="RefreshRight" circle size="small" @click="loadTelegramUsage(true)" :loading="loadingTelegramUsage" />
              </template>
              <template v-else>
                <template v-if="loadingDriveUsage">
                  <span class="header-usage-text">容量读取中...</span>
                </template>
                <template v-else-if="driveUsage?.supported && driveUsage.data">
                  <span class="header-usage-name">{{ currentRemote }}</span>
                  <span class="header-usage-text">{{ formatBytes(driveUsage.data.used) }} / {{ formatBytes(driveUsage.data.total) }}</span>
                  <el-tag size="small" round :type="usagePercent >= 90 ? 'danger' : usagePercent >= 75 ? 'warning' : 'success'">
                    {{ usagePercent.toFixed(1) }}%
                  </el-tag>
                </template>
                <template v-else>
                  <span class="header-usage-name">{{ currentRemote }}</span>
                  <span class="header-usage-text">{{ driveUsage?.error || '暂不支持容量统计' }}</span>
                </template>
                <el-button :icon="RefreshRight" circle size="small" @click="loadDriveUsage(true, true)" :loading="loadingDriveUsage" />
              </template>
            </div>
          </div>
        </div>
      </template>

      <div class="drive-topbar">
        <div class="drive-controls">
          <div class="drive-breadcrumb-card">
            <el-breadcrumb separator="/">
              <el-breadcrumb-item @click="navigateToPath('/')">
                <el-icon><HomeFilled /></el-icon>
                {{ isTelegramMode ? 'Telegram 频道' : '根目录' }}
              </el-breadcrumb-item>
              <el-breadcrumb-item
                v-for="segment in breadcrumbSegments"
                :key="segment.path"
                @click="navigateToPath(segment.path)"
              >
                {{ segment.label }}
              </el-breadcrumb-item>
            </el-breadcrumb>
          </div>

          <div class="drive-actions">
            <el-button-group class="view-mode-toggle">
              <el-button :type="viewMode === 'list' ? 'primary' : ''" @click="viewMode = 'list'">
                <el-icon><List /></el-icon>
              </el-button>
              <el-button :type="viewMode === 'grid' ? 'primary' : ''" @click="viewMode = 'grid'">
                <el-icon><Grid /></el-icon>
              </el-button>
            </el-button-group>

            <el-select
              v-model="currentSort"
              placeholder="排序"
              class="sort-select"
            >
              <template #prefix>
                <el-icon><Sort /></el-icon>
              </template>
              <el-option
                v-for="item in sortOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>

            <el-button
              v-if="isTelegramMode"
              type="danger"
              plain
              :icon="Delete"
              :disabled="telegramTotal === 0"
              @click="handleClearTelegramMedia"
            >
              清空 tg 网盘
            </el-button>

            <el-input
              v-model="searchKeyword"
              placeholder="搜索文件名"
              clearable
              class="search-input"
              :prefix-icon="Search"
            />
          </div>
        </div>
      </div>

      <div class="tg-drive-shell" v-loading="loading">
        <aside class="tg-filter-rail">
          <button
            v-for="filter in quickFilterOptions"
            :key="filter.key"
            class="tg-filter-pill"
            :class="{ 'is-active': currentFilter === filter.key }"
            @click="currentFilter = filter.key"
          >
            <span class="tg-filter-pill-head">
              <span>{{ filter.label }}</span>
              <span class="tg-filter-pill-count">{{ filter.count }}</span>
            </span>
            <span class="tg-filter-pill-desc">{{ filter.description }}</span>
          </button>
        </aside>

        <section class="tg-drive-main">
          <div class="tg-stream-header">
            <div>
              <div class="tg-stream-title">文件流</div>
              <div class="tg-stream-subtitle">
                {{ isTelegramMode ? 'Telegram 频道' : (currentRemote || '未选择存储') }} · {{ quickFilterOptions.find(item => item.key === currentFilter)?.label || '全部' }} · {{ visibleItemCount }} 项
              </div>
            </div>
            <el-tag round effect="plain">
              双击打开，单击查看详情
            </el-tag>
          </div>

          <div v-if="viewMode === 'list'" class="tg-stream-list">
            <div
              v-for="item in paginatedItems"
              :key="item.path"
              class="tg-file-row"
              :class="{ 'is-active': selectedItem?.path === item.path }"
              @click="selectItem(item)"
              @dblclick="handleRowClick(item)"
            >
              <div class="tg-file-avatar">
                <el-icon v-if="item.isDir" :size="22">
                  <Folder />
                </el-icon>
                <el-image
                  v-else-if="isImage(item.name)"
                  :src="getThumbnailUrl(item)"
                  fit="cover"
                  class="tg-file-thumb"
                >
                  <template #error>
                    <div class="tg-file-thumb-fallback">
                      <el-icon :size="22"><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
                <div v-else-if="isVideo(item.name)" class="tg-file-thumb-fallback is-video">
                  <el-icon :size="22"><VideoPlay /></el-icon>
                </div>
                <el-icon v-else :size="22">
                  <Document />
                </el-icon>
              </div>

              <div class="tg-file-body">
                <div class="tg-file-title-row">
                  <span class="tg-file-title" :title="item.name">{{ item.name }}</span>
                  <el-tag size="small" effect="plain" round>
                    {{ getItemTypeLabel(item) }}
                  </el-tag>
                </div>
                <div class="tg-file-meta">
                  {{ getItemMetaLine(item) }}
                </div>
                <div class="tg-file-path" :title="getItemPathHint(item)">
                  {{ getItemPathHint(item) }}
                </div>
              </div>

              <div class="tg-file-trailing">
                <div class="tg-file-date">{{ formatDate(item.modTime) }}</div>
                <div class="tg-file-actions">
                  <el-button link type="primary" @click.stop="handleRowClick(item)">
                    {{ item.isDir ? '进入' : '打开' }}
                  </el-button>
                  <el-button
                    v-if="!item.isDir"
                    link
                    :loading="Boolean(downloadingPaths[item.path])"
                    @click.stop="handleDownload(item)"
                  >
                    下载
                  </el-button>
                  <el-button link type="danger" @click.stop="handleDelete(item)">
                    删除
                  </el-button>
                </div>
              </div>
            </div>
            <el-empty v-if="paginatedItems.length === 0" description="当前筛选下没有文件" :image-size="72" />
          </div>

          <div v-else class="grid-view">
            <div
              v-for="item in paginatedItems"
              :key="item.path"
              class="grid-item"
              @click="handleRowClick(item)"
            >
              <div class="grid-item-preview">
                <el-icon v-if="item.isDir" :size="48" class="grid-icon">
                  <Folder />
                </el-icon>
                <el-image
                  v-else-if="isImage(item.name)"
                  :src="getThumbnailUrl(item)"
                  fit="cover"
                  class="grid-thumbnail"
                  lazy
                >
                  <template #placeholder>
                    <div class="image-placeholder">
                      <el-icon :size="48"><Picture /></el-icon>
                    </div>
                  </template>
                  <template #error>
                    <div class="image-placeholder">
                      <el-icon :size="48"><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
                <div v-else-if="isVideo(item.name)" class="grid-video">
                  <el-image
                    :src="getThumbnailUrl(item)"
                    fit="cover"
                    class="grid-thumbnail"
                    lazy
                  >
                    <template #placeholder>
                      <div class="video-placeholder">
                        <el-icon :size="48"><VideoPlay /></el-icon>
                      </div>
                    </template>
                    <template #error>
                      <div class="video-placeholder">
                        <el-icon :size="48"><VideoPlay /></el-icon>
                      </div>
                    </template>
                  </el-image>
                  <div class="video-badge">视频</div>
                </div>
                <el-icon v-else :size="48" class="grid-icon">
                  <Document />
                </el-icon>
              </div>
              <div class="grid-item-name" :title="item.name">{{ item.name }}</div>
              <div class="grid-item-info">
                <div v-if="!item.isDir" class="grid-item-size">{{ formatBytes(item.size) }}</div>
                <div class="grid-item-actions">
                  <el-button
                    v-if="!item.isDir"
                    circle
                    size="small"
                    :icon="Download"
                    :loading="Boolean(downloadingPaths[item.path])"
                    @click.stop="handleDownload(item)"
                  />
                  <el-button
                    circle
                    size="small"
                    type="danger"
                    :icon="Delete"
                    @click.stop="handleDelete(item)"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <aside class="tg-inspector" v-if="selectedItem">
          <div class="tg-inspector-preview" @click="!selectedItem.isDir && handleRowClick(selectedItem)">
            <el-icon v-if="selectedItem.isDir" :size="54">
              <Folder />
            </el-icon>
            <el-image
              v-else-if="isImage(selectedItem.name)"
              :src="getThumbnailUrl(selectedItem)"
              fit="cover"
              class="tg-inspector-image"
            >
              <template #error>
                <div class="tg-inspector-fallback">
                  <el-icon :size="54"><Picture /></el-icon>
                </div>
              </template>
            </el-image>
            <div v-else-if="isVideo(selectedItem.name)" class="tg-inspector-fallback is-video">
              <el-icon :size="54"><VideoPlay /></el-icon>
            </div>
            <div v-else class="tg-inspector-fallback">
              <el-icon :size="54"><Document /></el-icon>
            </div>
          </div>

          <div class="tg-inspector-title">{{ selectedItem.name }}</div>
          <div class="tg-inspector-subtitle">{{ getItemMetaLine(selectedItem) }}</div>

          <div class="tg-inspector-actions">
            <el-button type="primary" @click="handleRowClick(selectedItem)">
              {{ selectedItem.isDir ? '进入文件夹' : '打开预览' }}
            </el-button>
            <el-button v-if="!selectedItem.isDir" @click="handleDownload(selectedItem)" :loading="Boolean(downloadingPaths[selectedItem.path])">
              下载到本地
            </el-button>
            <el-button type="danger" plain @click="handleDelete(selectedItem)">
              {{ isTelegramMode && selectedItem.isDir ? '删除媒体组' : '删除' }}
            </el-button>
          </div>

          <div class="tg-inspector-meta">
            <template v-if="isTelegramMode && !selectedItem.isDir && telegramItemMeta[selectedItem.path]">
              <div v-if="telegramItemMeta[selectedItem.path].caption" class="tg-inspector-meta-row tg-caption-row">
                <span>说明</span>
                <span>{{ telegramItemMeta[selectedItem.path].caption }}</span>
              </div>
              <div class="tg-inspector-meta-row">
                <span>消息 ID</span>
                <span>{{ telegramItemMeta[selectedItem.path].messageId }}</span>
              </div>
              <div v-if="telegramItemMeta[selectedItem.path].duration" class="tg-inspector-meta-row">
                <span>时长</span>
                <span>{{ Math.floor(telegramItemMeta[selectedItem.path].duration! / 60) }}:{{ String(telegramItemMeta[selectedItem.path].duration! % 60).padStart(2, '0') }}</span>
              </div>
            </template>
            <template v-if="isTelegramMode && selectedItem.isDir && telegramGroupMeta[selectedItem.path]">
              <div class="tg-inspector-meta-row">
                <span>媒体组</span>
                <span>{{ telegramGroupMeta[selectedItem.path].count }} 个文件</span>
              </div>
              <div class="tg-inspector-meta-row">
                <span>组大小</span>
                <span>{{ formatBytes(telegramGroupMeta[selectedItem.path].size) }}</span>
              </div>
            </template>
            <div v-if="!isTelegramMode" class="tg-inspector-meta-row">
              <span>路径</span>
              <span>{{ selectedItem.path }}</span>
            </div>
            <div class="tg-inspector-meta-row">
              <span>时间</span>
              <span>{{ formatDate(selectedItem.modTime) }}</span>
            </div>
            <div class="tg-inspector-meta-row">
              <span>大小</span>
              <span>{{ selectedItem.isDir ? '-' : formatBytes(selectedItem.size) }}</span>
            </div>
            <div class="tg-inspector-meta-row">
              <span>存储</span>
              <span>{{ isTelegramMode ? 'Telegram 频道' : currentRemote }}</span>
            </div>
          </div>
        </aside>
      </div>

      <!-- 分页 -->
      <div v-if="!isTelegramMode || !currentTelegramGroupId" class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="paginationTotal"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!loading && visibleItemCount === 0" description="此目录为空" />
    </el-card>

    <!-- 图片预览 -->
    <el-image-viewer
      v-if="showPreview && previewType === 'image'"
      :url-list="[previewUrl]"
      @close="closePreview"
      hide-on-click-modal
    />

    <!-- 视频播放 -->
    <el-dialog
      v-model="showPreview"
      v-if="previewType === 'video'"
      :title="previewItem?.name"
      width="80%"
      destroy-on-close
      @close="closePreview"
      center
      class="video-dialog"
    >
      <div class="video-container">
        <div v-if="previewLoading" class="preview-loading-card">
          <div class="preview-loading-title">正在准备本地播放</div>
          <div class="preview-loading-subtitle">
            桌面端会先缓存一段视频到本地，再切换到本地流播放。
          </div>
          <el-progress
            :percentage="previewProgressPercent"
            :indeterminate="!previewTransferStatus?.totalBytes"
            :duration="2"
            status="success"
          />
          <div class="preview-loading-meta">
            {{ previewProgressText }}
          </div>
        </div>
        <VideoPlayer 
          v-else-if="showPreview && previewType === 'video' && previewUrl"
          :src="previewUrl" 
          :type="getVideoType(previewItem?.name)"
          :remote="currentRemote"
          :path="previewItem?.path"
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { HomeFilled, Document, Folder, Search, List, Grid, Picture, VideoPlay, Sort, Download, Delete, RefreshRight } from '@element-plus/icons-vue'
import { getRcloneRemotes, browseDrive, getThumbnail, deleteFile, getDriveUsage, browseTelegram, getTelegramUsage, deleteTelegramItem, deleteTelegramGroup, clearTelegramMedia, type RcloneRemote, type DriveItem, type DriveUsageResponse, type TelegramMediaItem, type TelegramUsageStats } from '@/api'
import VideoPlayer from '@/components/VideoPlayer.vue'
import {
  getDesktopTransferStatus,
  prepareDesktopPreviewFile,
  startDesktopPreviewStream,
  toDesktopAssetUrl,
  type DesktopTransferStatus,
} from '@/utils/desktop'
import { useDesktopDownloads } from '@/composables/useDesktopDownloads'
import { buildAuthorizedApiUrl, toAbsoluteServerUrl } from '@/utils/runtime'

const {
  downloadingPaths,
  startTrackedDesktopDownload,
} = useDesktopDownloads()

interface RemoteUsageState {
  response?: DriveUsageResponse
  loading: boolean
}

type QuickFilter = 'all' | 'folders' | 'videos' | 'images' | 'documents' | 'recent'

const TELEGRAM_REMOTE_NAME = '__telegram__'

interface TelegramItemMeta {
  streamUrl: string
  hash: string
  caption: string | null
  duration: number | null
  messageId: number
  supportsStreaming: boolean
  mediaGroupId: string | null
}

interface TelegramGroupMeta {
  id: string
  title: string
  count: number
  size: number
  modTime?: string
}

const telegramItemMeta = ref<Record<string, TelegramItemMeta>>({})
const telegramGroupMeta = ref<Record<string, TelegramGroupMeta>>({})
const telegramTotal = ref(0)
const telegramUsage = ref<TelegramUsageStats | null>(null)
const loadingTelegramUsage = ref(false)

const isTelegramMode = computed(() => currentRemote.value === TELEGRAM_REMOTE_NAME)
const TELEGRAM_GROUP_PATH_PREFIX = '/__tg_group__/'

const availableRemotes = ref<RcloneRemote[]>([])
const currentRemote = ref('')
const currentPath = ref('/')
const items = ref<DriveItem[]>([])
const loading = ref(false)
const remoteUsageStates = ref<Record<string, RemoteUsageState>>({})
const currentFilter = ref<QuickFilter>('all')
const selectedItemPath = ref('')

// 搜索和分页
const searchKeyword = ref('')
const currentPage = ref(1)
const pageSize = ref(20)

// 视图模式
const viewMode = ref<'list' | 'grid'>('list')

// 排序状态
const sortBy = ref<'name' | 'time'>('time')
const sortDesc = ref(true) // 默认降序(最新的在前)

// 排序选项
const sortOptions = [
  { label: '时间 (新→旧)', value: 'time-desc' },
  { label: '时间 (旧→新)', value: 'time-asc' },
  { label: '名称 (A→Z)', value: 'name-asc' },
  { label: '名称 (Z→A)', value: 'name-desc' },
]

const currentSort = computed({
  get: () => `${sortBy.value}-${sortDesc.value ? 'desc' : 'asc'}`,
  set: (val) => {
    const [field, order] = val.split('-')
    sortBy.value = field as 'name' | 'time'
    sortDesc.value = order === 'desc'
  }
})

const currentRemoteInfo = computed(() => {
  return availableRemotes.value.find(remote => remote.name === currentRemote.value) || null
})

const currentRemoteState = computed(() => {
  if (!currentRemote.value) return null
  return remoteUsageStates.value[currentRemote.value] || null
})

const driveUsage = computed(() => currentRemoteState.value?.response || null)
const loadingDriveUsage = computed(() => currentRemoteState.value?.loading || false)

const usagePercent = computed(() => {
  const total = driveUsage.value?.data?.total
  const used = driveUsage.value?.data?.used
  if (!total || !used || total <= 0) return 0
  return Math.min(100, Number(((used / total) * 100).toFixed(1)))
})

const usageProgressColor = computed(() => {
  if (usagePercent.value >= 90) return '#ef4444'
  if (usagePercent.value >= 75) return '#f59e0b'
  return '#10b981'
})

// 计算属性
const currentTelegramGroupId = computed(() => (
  isTelegramMode.value && currentPath.value.startsWith(TELEGRAM_GROUP_PATH_PREFIX)
    ? currentPath.value.slice(TELEGRAM_GROUP_PATH_PREFIX.length)
    : null
))

const breadcrumbSegments = computed(() => {
  if (isTelegramMode.value) {
    const groupId = currentTelegramGroupId.value
    if (!groupId) return []
    const groupPath = `${TELEGRAM_GROUP_PATH_PREFIX}${groupId}`
    return [{
      path: groupPath,
      label: telegramGroupMeta.value[groupPath]?.title || '媒体组',
    }]
  }

  const path = currentPath.value
  if (path === '/') return []

  return path.split('/').filter(Boolean).map((segment, index) => ({
    path: `/${path.split('/').filter(Boolean).slice(0, index + 1).join('/')}`,
    label: segment,
  }))
})

function matchesQuickFilter(item: DriveItem, filter: QuickFilter): boolean {
  switch (filter) {
    case 'folders':
      return item.isDir
    case 'videos':
      return !item.isDir && isVideo(item.name)
    case 'images':
      return !item.isDir && isImage(item.name)
    case 'documents':
      return !item.isDir && !isVideo(item.name) && !isImage(item.name)
    case 'recent':
      return !item.isDir
    default:
      return true
  }
}

const quickFilterOptions = computed(() => {
  if (isTelegramMode.value) {
    const u = telegramUsage.value
    return [
      { key: 'all' as QuickFilter, label: '全部', description: '频道中的所有媒体文件', count: u?.total_count || 0 },
      { key: 'videos' as QuickFilter, label: '视频', description: '在线播放和本地缓存优先', count: u?.videos || 0 },
      { key: 'images' as QuickFilter, label: '图片', description: '快速预览图片资源', count: u?.images || 0 },
      { key: 'documents' as QuickFilter, label: '文档', description: '压缩包、PDF 和普通文件', count: u?.documents || 0 },
    ]
  }

  const definitions: Array<{ key: QuickFilter; label: string; description: string }> = [
    { key: 'all', label: '全部', description: '像 Telegram 媒体页一样汇总当前目录' },
    { key: 'folders', label: '文件夹', description: '先处理目录导航和归档' },
    { key: 'videos', label: '视频', description: '在线播放和本地缓存优先' },
    { key: 'images', label: '图片', description: '快速预览图片资源' },
    { key: 'documents', label: '文档', description: '压缩包、PDF 和普通文件' },
    { key: 'recent', label: '最近', description: '按时间倒序查看最近文件' },
  ]

  return definitions.map(item => ({
    ...item,
    count: items.value.filter(file => matchesQuickFilter(file, item.key)).length,
  }))
})

const telegramVisibleItems = computed(() => {
  if (!isTelegramMode.value) return []

  const groupId = currentTelegramGroupId.value
  if (groupId) {
    return items.value.filter(item => telegramItemMeta.value[item.path]?.mediaGroupId === groupId)
  }

  const grouped = new Map<string, DriveItem[]>()
  const singles: DriveItem[] = []
  const nextGroupMeta: Record<string, TelegramGroupMeta> = {}

  for (const item of items.value) {
    const mediaGroupId = telegramItemMeta.value[item.path]?.mediaGroupId
    if (!mediaGroupId) {
      singles.push(item)
      continue
    }

    const bucket = grouped.get(mediaGroupId) || []
    bucket.push(item)
    grouped.set(mediaGroupId, bucket)
  }

  const folders = Array.from(grouped.entries()).map(([mediaGroupId, members]) => {
    const first = members[0]
    const title = buildTelegramGroupTitle(mediaGroupId, members)
    const groupPath = `${TELEGRAM_GROUP_PATH_PREFIX}${mediaGroupId}`
    nextGroupMeta[groupPath] = {
      id: mediaGroupId,
      title,
      count: members.length,
      size: members.reduce((sum, member) => sum + (member.size || 0), 0),
      modTime: members[0]?.modTime,
    }

    return {
      name: title,
      path: groupPath,
      size: nextGroupMeta[groupPath].size,
      mimeType: '',
      modTime: first?.modTime,
      isDir: true,
    } satisfies DriveItem
  })

  telegramGroupMeta.value = nextGroupMeta
  return [...folders, ...singles]
})

const filteredItems = computed(() => {
  if (isTelegramMode.value) return telegramVisibleItems.value

  let result = items.value.filter(item => matchesQuickFilter(item, currentFilter.value))
  
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(item => item.name.toLowerCase().includes(keyword))
  }
  
  result.sort((a, b) => {
    if (currentFilter.value === 'recent') {
      const timeA = a.modTime ? new Date(a.modTime).getTime() : 0
      const timeB = b.modTime ? new Date(b.modTime).getTime() : 0
      return timeB - timeA
    }

    if (a.isDir !== b.isDir) {
      return a.isDir ? -1 : 1
    }
    
    let comparison = 0
    
    if (sortBy.value === 'time') {
      const timeA = a.modTime ? new Date(a.modTime).getTime() : 0
      const timeB = b.modTime ? new Date(b.modTime).getTime() : 0
      comparison = timeA - timeB
    } else {
      comparison = a.name.localeCompare(b.name)
    }
    
    return sortDesc.value ? -comparison : comparison
  })
  
  return result
})

const paginatedItems = computed(() => {
  if (isTelegramMode.value) return filteredItems.value
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredItems.value.slice(start, end)
})

const visibleItemCount = computed(() => filteredItems.value.length)
const paginationTotal = computed(() => (
  isTelegramMode.value && currentTelegramGroupId.value
    ? filteredItems.value.length
    : isTelegramMode.value
      ? telegramTotal.value
      : filteredItems.value.length
))

const selectedItem = computed(() => {
  return paginatedItems.value.find(item => item.path === selectedItemPath.value) || paginatedItems.value[0] || null
})

// 文件类型判断
function isImage(filename: string): boolean {
  const imageExts = ['.jpg', '.jpeg', '.png', '.gif', '.bmp', '.webp', '.svg', '.ico']
  return imageExts.some(ext => filename.toLowerCase().endsWith(ext))
}

function isVideo(filename: string): boolean {
  const videoExts = ['.mp4', '.avi', '.mkv', '.mov', '.wmv', '.flv', '.webm', '.m4v']
  return videoExts.some(ext => filename.toLowerCase().endsWith(ext))
}

function getVideoType(filename: string | undefined): string {
  if (!filename) return ''
  const parts = filename.split('.')
  if (parts.length < 2) return ''
  const ext = parts.pop()?.toLowerCase()
  
  if (ext === 'mkv') return 'video/x-matroska' // video.js might need specific type for mkv if supported, or just let browser handle
  // For common formats:
  if (ext === 'mp4') return 'video/mp4'
  if (ext === 'webm') return 'video/webm'
  if (ext === 'ogg') return 'video/ogg'
  return ''
}

function getItemTypeLabel(item: DriveItem): string {
  if (item.isDir) return isTelegramMode.value ? '媒体组' : '文件夹'
  if (isVideo(item.name)) return '视频'
  if (isImage(item.name)) return '图片'
  return '文件'
}

function buildTelegramGroupTitle(mediaGroupId: string, members: DriveItem[]): string {
  const first = members[0]
  const firstMeta = first ? telegramItemMeta.value[first.path] : null
  const baseTitle = firstMeta?.caption?.trim() || first?.name || `媒体组 ${mediaGroupId.slice(-6)}`
  return `${baseTitle} · ${members.length} 项`
}

function formatRelativeTime(dateStr: string | undefined): string {
  if (!dateStr) return '未知时间'

  const timestamp = new Date(dateStr).getTime()
  if (Number.isNaN(timestamp)) return '未知时间'

  const diff = timestamp - Date.now()
  const abs = Math.abs(diff)
  const minute = 60 * 1000
  const hour = 60 * minute
  const day = 24 * hour

  const formatter = new Intl.RelativeTimeFormat('zh-CN', { numeric: 'auto' })

  if (abs < hour) {
    return formatter.format(Math.round(diff / minute), 'minute')
  }
  if (abs < day) {
    return formatter.format(Math.round(diff / hour), 'hour')
  }
  return formatter.format(Math.round(diff / day), 'day')
}

function getItemMetaLine(item: DriveItem): string {
  if (item.isDir) {
    if (isTelegramMode.value) {
      const group = telegramGroupMeta.value[item.path]
      const parts = ['媒体组']
      if (group) {
        parts.push(`${group.count} 个文件`)
        if (group.size > 0) {
          parts.push(formatBytes(group.size))
        }
        if (group.modTime) {
          parts.push(formatRelativeTime(group.modTime))
        }
      }
      return parts.join(' · ')
    }
    return `${getItemTypeLabel(item)} · ${formatRelativeTime(item.modTime)}`
  }

  const parts = [getItemTypeLabel(item), formatBytes(item.size)]

  if (isTelegramMode.value) {
    const meta = telegramItemMeta.value[item.path]
    if (meta?.duration) {
      const m = Math.floor(meta.duration / 60)
      const s = meta.duration % 60
      parts.push(`${m}:${String(s).padStart(2, '0')}`)
    }
  }

  parts.push(formatRelativeTime(item.modTime))
  return parts.join(' · ')
}

function getItemPathHint(item: DriveItem): string {
  if (!isTelegramMode.value) {
    return item.path
  }

  if (item.isDir) {
    const group = telegramGroupMeta.value[item.path]
    return group ? `${group.count} 个文件` : '媒体组'
  }

  return telegramItemMeta.value[item.path]?.caption || item.path
}

function selectItem(item: DriveItem) {
  selectedItemPath.value = item.path
}

// 缩略图URL响应式存储
const thumbnailUrls = ref<Record<string, string>>({})
// 缩略图加载队列
const thumbnailQueue = ref<DriveItem[]>([])
const isProcessingQueue = ref(false)

// 获取缩略图URL - 返回响应式的URL
function getThumbnailUrl(item: DriveItem): string {
  const cacheKey = `${currentRemote.value}:${item.path}`
  return thumbnailUrls.value[cacheKey] || ''
}

// 处理缩略图队列
async function processThumbnailQueue() {
  if (isProcessingQueue.value || thumbnailQueue.value.length === 0) return
  
  isProcessingQueue.value = true
  
  try {
    while (thumbnailQueue.value.length > 0) {
      // 取出第一个任务（已按时间排序）
      const item = thumbnailQueue.value.shift()
      if (!item) continue
      
      const cacheKey = `${currentRemote.value}:${item.path}`
      
      // 如果已有缓存，跳过
      if (thumbnailUrls.value[cacheKey]) continue
      
      const remoteInfo = availableRemotes.value.find(r => r.name === currentRemote.value)
      const remoteType = remoteInfo?.type || 'onedrive'
      
      try {
        console.log('正在加载缩略图:', item.name)
        const response = await getThumbnail(currentRemote.value, item.path, remoteType, currentPath.value, item.id || '')
        
        if (response.success && response.thumbnail_url) {
          thumbnailUrls.value = {
            ...thumbnailUrls.value,
            [cacheKey]: response.thumbnail_url
          }
        }
      } catch (err) {
        console.error('获取缩略图失败:', item.name, err)
      }
      
      // 稍微延迟一下，给浏览器喘息机会，也避免请求过于密集
      await new Promise(resolve => setTimeout(resolve, 100))
    }
  } finally {
    isProcessingQueue.value = false
  }
}

// 将当前页面的图片/视频添加到加载队列
function queueThumbnails() {
  if (viewMode.value !== 'grid') return
  
  const itemsToLoad = paginatedItems.value.filter(item => {
    if (item.isDir) return false
    if (!isImage(item.name) && !isVideo(item.name)) return false
    
    const cacheKey = `${currentRemote.value}:${item.path}`
    return !thumbnailUrls.value[cacheKey]
  })
  
  // 按修改时间降序排序（最新的优先）
  itemsToLoad.sort((a, b) => {
    let timeA = 0
    let timeB = 0
    
    if (a.modTime) {
      const t = new Date(a.modTime).getTime()
      if (!isNaN(t)) timeA = t
    }
    
    if (b.modTime) {
      const t = new Date(b.modTime).getTime()
      if (!isNaN(t)) timeB = t
    }
    
    return timeB - timeA
  })
  
  if (itemsToLoad.length > 0) {
    console.log('Thumbnail queue sorted (desc). First:', itemsToLoad[0].name, itemsToLoad[0].modTime)
    console.log('Last:', itemsToLoad[itemsToLoad.length-1].name, itemsToLoad[itemsToLoad.length-1].modTime)
  }
  
  // 更新队列：保留不在新列表中的旧任务（可选），这里简单起见，直接用新页面的任务覆盖
  // 或者追加到队首？用户说"优先日期加载最新"，通常是指当前视图的最新。
  // 为了响应分页变化，我们应该优先加载当前可视区域的内容。
  
  // 策略：清空旧队列，只加载当前页面的任务，确保当前页面优先
  thumbnailQueue.value = itemsToLoad
  
  processThumbnailQueue()
}




// 加载 remotes 列表
async function loadRemotes() {
  try {
    const response = await getRcloneRemotes()
    const remotes: RcloneRemote[] = [
      { name: TELEGRAM_REMOTE_NAME, type: 'telegram' },
    ]
    if (response.success && response.remotes) {
      remotes.push(...response.remotes)
    }
    availableRemotes.value = remotes
    if (!currentRemote.value) {
      currentRemote.value = remotes[0].name
    }
  } catch (err) {
    console.error('加载 remotes 失败:', err)
    availableRemotes.value = [{ name: TELEGRAM_REMOTE_NAME, type: 'telegram' }]
    currentRemote.value = TELEGRAM_REMOTE_NAME
  }
}

async function fetchRemoteUsage(remote: string, force = false, showError = false) {
  if (!remote) return null

  const currentState = remoteUsageStates.value[remote]
  if (!force && currentState?.response) {
    return currentState.response
  }
  if (currentState?.loading) {
    return currentState.response || null
  }

  remoteUsageStates.value = {
    ...remoteUsageStates.value,
    [remote]: {
      response: currentState?.response,
      loading: true
    }
  }

  try {
    const response = await getDriveUsage(remote)
    remoteUsageStates.value = {
      ...remoteUsageStates.value,
      [remote]: {
        response,
        loading: false
      }
    }
    if (!response.success && showError) {
      ElMessage.error(response.error || '获取网盘容量失败')
    }
    return response
  } catch (err: any) {
    console.error('加载网盘容量失败:', err)
    const response: DriveUsageResponse = {
      success: false,
      supported: false,
      remote,
      error: err.message || '获取网盘容量失败'
    }
    remoteUsageStates.value = {
      ...remoteUsageStates.value,
      [remote]: {
        response,
        loading: false
      }
    }
    if (showError) {
      ElMessage.error(err.message || '获取网盘容量失败')
    }
    return response
  }
}

async function preloadRemoteUsages() {
  const tasks = availableRemotes.value.map(remote => fetchRemoteUsage(remote.name))
  await Promise.allSettled(tasks)
}

async function loadDriveUsage(force = false, showError = false) {
  if (!currentRemote.value) return
  await fetchRemoteUsage(currentRemote.value, force, showError)
}

function getRemoteUsagePercent(remote: string): number | null {
  const usage = remoteUsageStates.value[remote]?.response
  const total = usage?.data?.total
  const used = usage?.data?.used
  if (!usage?.supported || !total || used === undefined || used === null || total <= 0) return null
  return Math.min(100, (used / total) * 100)
}

function getRemoteUsageSummary(remote: string): string {
  const state = remoteUsageStates.value[remote]
  if (state?.loading) return '容量读取中...'
  const usage = state?.response
  if (!usage) return '等待加载容量'
  if (!usage.success) return '容量读取失败'
  if (!usage.supported || !usage.data) return '暂不支持容量统计'

  const used = formatBytes(usage.data.used ?? 0)
  const total = formatBytes(usage.data.total ?? 0)
  return `${used} / ${total}`
}

function tgMimeFilter(): string | undefined {
  const map: Record<string, string> = {
    videos: 'video',
    images: 'image',
    documents: 'document',
  }
  return map[currentFilter.value]
}

function mapTelegramItem(tg: TelegramMediaItem): DriveItem {
  const fallbackName = `media_${tg.message_id}${tg.mime_type ? '.' + tg.mime_type.split('/')[1] : ''}`
  const path = `tg://${tg.message_id}`
  telegramItemMeta.value[path] = {
    streamUrl: tg.stream_url,
    hash: tg.hash,
    caption: tg.caption,
    duration: tg.duration,
    messageId: tg.message_id,
    supportsStreaming: !!tg.supports_streaming,
    mediaGroupId: tg.media_group_id,
  }
  return {
    name: tg.file_name || fallbackName,
    path,
    size: tg.file_size || 0,
    mimeType: tg.mime_type || '',
    modTime: tg.message_date,
    isDir: false,
  }
}

async function browseTelegramChannel() {
  loading.value = true
  try {
    const response = await browseTelegram({
      page: currentPage.value,
      page_size: pageSize.value,
      search: searchKeyword.value || undefined,
      type: tgMimeFilter(),
      sort_by: sortBy.value === 'time' ? 'message_date' : 'file_name',
      sort_desc: sortDesc.value,
    })
    if (response.success) {
      telegramTotal.value = response.total
      items.value = response.items.map(mapTelegramItem)
      if (currentTelegramGroupId.value && !items.value.some(item => telegramItemMeta.value[item.path]?.mediaGroupId === currentTelegramGroupId.value)) {
        currentPath.value = '/'
      }
      if (!items.value.some(i => i.path === selectedItemPath.value)) {
        selectedItemPath.value = items.value[0]?.path || ''
      }
    } else {
      ElMessage.error(response.error || '获取 Telegram 文件列表失败')
      items.value = []
      telegramTotal.value = 0
    }
  } catch (err: any) {
    console.error('Telegram 浏览失败:', err)
    ElMessage.error(err.message || '获取 Telegram 文件列表失败')
    items.value = []
    telegramTotal.value = 0
  } finally {
    loading.value = false
  }
}

async function loadTelegramUsage(force = false) {
  if (!force && telegramUsage.value) return
  loadingTelegramUsage.value = true
  try {
    const resp = await getTelegramUsage()
    if (resp.success && resp.data) {
      telegramUsage.value = resp.data
    }
  } catch (err) {
    console.error('获取 Telegram 容量失败:', err)
  } finally {
    loadingTelegramUsage.value = false
  }
}

// 浏览目录
async function browse() {
  if (!currentRemote.value) return

  if (isTelegramMode.value) {
    await browseTelegramChannel()
    return
  }

  loading.value = true
  try {
    const response = await browseDrive(currentRemote.value, currentPath.value)
    if (response.success && response.items) {
      items.value = response.items
      currentPage.value = 1
      selectedItemPath.value = response.items[0]?.path || ''
    } else {
      ElMessage.error(response.error || '获取文件列表失败')
      items.value = []
      selectedItemPath.value = ''
    }
  } catch (err: any) {
    console.error('浏览失败:', err)
    ElMessage.error(err.message || '获取文件列表失败')
    items.value = []
    selectedItemPath.value = ''
  } finally {
    loading.value = false
  }
}

// Remote 改变
function handleRemoteChange() {
  currentPath.value = '/'
  currentPage.value = 1
  currentFilter.value = 'all'
  searchKeyword.value = ''

  if (isTelegramMode.value) {
    loadTelegramUsage()
  } else if (!remoteUsageStates.value[currentRemote.value]?.response) {
    loadDriveUsage()
  }
  browse()
}

// 下载文件
async function handleDownload(item: DriveItem) {
  if (item.isDir) return

  let url: string
  if (isTelegramMode.value) {
    url = getTelegramDirectLink(item)
  } else {
    url = buildAuthorizedApiUrl('/api/rclone/file', {
      remote: currentRemote.value,
      path: item.path,
      download: true,
    })
  }

  await startTrackedDesktopDownload({
    sourceUrl: url,
    remote: isTelegramMode.value ? 'telegram' : currentRemote.value,
    remotePath: item.path,
    fileName: item.name,
    pathKey: item.path,
  })
}

function getTelegramGroupIdFromItem(item: DriveItem): string | null {
  if (item.path.startsWith(TELEGRAM_GROUP_PATH_PREFIX)) {
    return item.path.slice(TELEGRAM_GROUP_PATH_PREFIX.length)
  }

  return telegramItemMeta.value[item.path]?.mediaGroupId || null
}

async function refreshTelegramViewAfterMutation() {
  await loadTelegramUsage(true)
  await browseTelegramChannel()
}

async function handleClearTelegramMedia() {
  await ElMessageBox.confirm(
    '确定要清空整个 tg 网盘吗？这会删除频道内对应消息，并清理相关下载/上传记录。',
    '确认清空',
    {
      confirmButtonText: '清空',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )

  loading.value = true
  try {
    const response = await clearTelegramMedia()
    if (response.success) {
      currentPath.value = '/'
      selectedItemPath.value = ''
      await refreshTelegramViewAfterMutation()
      ElMessage.success(response.message || 'tg 网盘已清空')
    } else {
      ElMessage.error(response.error || '清空 tg 网盘失败')
    }
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      console.error('清空 tg 网盘失败:', err)
      ElMessage.error(err.message || '清空 tg 网盘失败')
    }
  } finally {
    loading.value = false
  }
}

// 删除文件
function handleDelete(item: DriveItem) {
  if (isTelegramMode.value) {
    const isGroup = item.isDir
    const mediaGroupId = isGroup ? getTelegramGroupIdFromItem(item) : null
    const messageId = !isGroup ? telegramItemMeta.value[item.path]?.messageId : null
    const targetLabel = isGroup ? '媒体组' : '文件'
    const targetName = item.name

    if (isGroup && !mediaGroupId) {
      ElMessage.error('媒体组标识缺失，无法删除')
      return
    }
    if (!isGroup && !messageId) {
      ElMessage.error('消息 ID 缺失，无法删除')
      return
    }

    ElMessageBox.confirm(
      `确定要删除 ${targetLabel} "${targetName}" 吗？这会删除频道内对应消息，并清理相关记录。`,
      '确认删除',
      {
        confirmButtonText: '删除',
        cancelButtonText: '取消',
        type: 'warning',
      }
    ).then(async () => {
      loading.value = true
      try {
        const response = isGroup
          ? await deleteTelegramGroup(mediaGroupId!)
          : await deleteTelegramItem(messageId!)

        if (response.success) {
          if (isGroup && currentTelegramGroupId.value === mediaGroupId) {
            currentPath.value = '/'
          }
          await refreshTelegramViewAfterMutation()
          ElMessage.success(response.message || '删除成功')
        } else {
          ElMessage.error(response.error || '删除失败')
        }
      } catch (err: any) {
        console.error('删除 tg 网盘项目失败:', err)
        ElMessage.error(err.message || '删除失败')
      } finally {
        loading.value = false
      }
    }).catch(() => {
      // 取消删除
    })
    return
  }
  ElMessageBox.confirm(
    `确定要删除 ${item.isDir ? '文件夹' : '文件'} "${item.name}" 吗？此操作不可恢复。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning'
    }
  ).then(async () => {
    loading.value = true
    try {
      const response = await deleteFile(currentRemote.value, item.path, item.isDir)
      if (response.success) {
        ElMessage.success('删除成功')
        // 刷新列表
        browse()
      } else {
        ElMessage.error(response.error || '删除失败')
      }
    } catch (err: any) {
      console.error('删除失败:', err)
      ElMessage.error(err.message || '删除失败')
    } finally {
      loading.value = false
    }
  }).catch(() => {
    // 取消删除
  })
}

// 预览状态
const showPreview = ref(false)
const previewItem = ref<DriveItem | null>(null)
const previewType = ref<'image' | 'video' | 'unknown'>('unknown')
const previewUrl = ref('')
const previewLoading = ref(false)
const previewTransferStatus = ref<DesktopTransferStatus | null>(null)
let previewRequestToken = 0

const previewProgressPercent = computed(() => {
  if (!previewTransferStatus.value) return 0
  return Math.min(100, Math.max(0, Number(previewTransferStatus.value.progressPercent || 0)))
})

const previewProgressText = computed(() => {
  const status = previewTransferStatus.value
  if (!status) return '正在准备本地播放缓存...'
  if (status.totalBytes && status.totalBytes > 0) {
    return `已缓存 ${formatBytes(status.downloadedBytes)} / ${formatBytes(status.totalBytes)}`
  }
  return `已缓存 ${formatBytes(status.downloadedBytes)}`
})

function getSourceUrlForItem(row: DriveItem): string {
  if (isTelegramMode.value) {
    return getTelegramDirectLink(row)
  }
  return buildAuthorizedApiUrl('/api/rclone/file', {
    remote: currentRemote.value,
    path: row.path,
  })
}

function getTelegramDirectLink(row: DriveItem): string {
  const meta = telegramItemMeta.value[row.path]
  const rawStreamUrl = meta?.streamUrl?.trim()
  const fallbackShortPath = meta?.hash && meta?.messageId ? `/${meta.hash}${meta.messageId}` : null

  if (!rawStreamUrl && !fallbackShortPath) {
    throw new Error('Telegram 直链地址缺失，请刷新列表后重试')
  }

  if (rawStreamUrl && /^https?:\/\//i.test(rawStreamUrl)) {
    return rawStreamUrl
  }

  const normalizedPath = rawStreamUrl
    ? `/${rawStreamUrl.replace(/^\/+/, '')}`
    : fallbackShortPath!
  return toAbsoluteServerUrl(normalizedPath)
}

async function preparePreviewSource(row: DriveItem): Promise<string> {
  const sourceUrl = getSourceUrlForItem(row)

  const result = await prepareDesktopPreviewFile({
    sourceUrl,
    remote: isTelegramMode.value ? 'telegram' : currentRemote.value,
    remotePath: row.path,
    fileName: row.name,
  })

  return toDesktopAssetUrl(result.localPath)
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

async function waitForPreviewReady(transferId: string, token: number): Promise<void> {
  while (token === previewRequestToken && showPreview.value) {
    const status = await getDesktopTransferStatus(transferId)
    previewTransferStatus.value = status

    if (status.state === 'error') {
      throw new Error(status.error || '本地播放缓存失败')
    }

    if (status.readyForPreview) {
      return
    }

    await sleep(350)
  }

  throw new Error('预览已取消')
}

// 点击行
async function handleRowClick(row: DriveItem) {
  if (row.isDir) {
    // 进入目录
    navigateToPath(row.path)
  } else {
    // 预览文件
    if (isImage(row.name)) {
      previewType.value = 'image'
      previewItem.value = row
      previewLoading.value = true
      try {
        previewUrl.value = await preparePreviewSource(row)
        showPreview.value = true
      } catch (err: any) {
        console.error('准备图片预览失败:', err)
        ElMessage.error(err.message || '准备图片预览失败')
        closePreview()
      } finally {
        previewLoading.value = false
      }
    } else if (isVideo(row.name)) {
      previewType.value = 'video'
      previewItem.value = row
      previewUrl.value = ''
      previewTransferStatus.value = null
      showPreview.value = true
      previewLoading.value = true
      const token = ++previewRequestToken
      try {
        const sourceUrl = getSourceUrlForItem(row)
        const session = await startDesktopPreviewStream({
          sourceUrl,
          remote: isTelegramMode.value ? 'telegram' : currentRemote.value,
          remotePath: row.path,
          fileName: row.name,
        })

        if (token !== previewRequestToken || !showPreview.value) {
          return
        }

        await waitForPreviewReady(session.transferId, token)

        if (token !== previewRequestToken || !showPreview.value) {
          return
        }

        previewUrl.value = session.streamUrl
      } catch (err: any) {
        if (err?.message !== '预览已取消') {
          console.error('准备视频预览失败:', err)
          ElMessage.error(err.message || '准备视频预览失败')
        }
        closePreview()
      } finally {
        if (token === previewRequestToken) {
          previewLoading.value = false
        }
      }
    } else {
      ElMessage.info('暂不支持预览此类型文件')
    }
  }
}

// 关闭预览
function closePreview() {
  previewRequestToken += 1
  showPreview.value = false
  previewItem.value = null
  previewUrl.value = ''
  previewType.value = 'unknown'
  previewLoading.value = false
  previewTransferStatus.value = null
}

// 导航到路径
function navigateToPath(path: string) {
  currentPath.value = path || '/'
  if (isTelegramMode.value) {
    return
  }
  browse()
}

// 格式化文件大小
function formatBytes(bytes: number | undefined): string {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
}

function formatCount(value: number | undefined | null): string {
  if (value === undefined || value === null) return '-'
  return new Intl.NumberFormat('zh-CN').format(value)
}

// 格式化日期
function formatDate(dateStr: string | undefined): string {
  if (!dateStr) return '-'
  try {
    const date = new Date(dateStr)
    return date.toLocaleString('zh-CN')
  } catch {
    return '-'
  }
}

onMounted(async () => {
  await loadRemotes()
  if (currentRemote.value) {
    if (isTelegramMode.value) {
      loadTelegramUsage()
    } else {
      void preloadRemoteUsages()
    }
    browse()
  }
})

// 监听视图模式变化
watch(viewMode, (newMode) => {
  if (newMode === 'grid') {
    queueThumbnails()
  }
})

watch([currentFilter, searchKeyword], () => {
  currentPage.value = 1
  if (isTelegramMode.value) {
    browseTelegramChannel()
  }
})

watch([currentPage, pageSize], () => {
  if (isTelegramMode.value && !currentTelegramGroupId.value) {
    browseTelegramChannel()
  }
})

watch([sortBy, sortDesc], () => {
  if (isTelegramMode.value) {
    currentPage.value = 1
    browseTelegramChannel()
  }
})

// 监听分页数据变化
watch(paginatedItems, () => {
    if (!paginatedItems.value.some(item => item.path === selectedItemPath.value)) {
      selectedItemPath.value = paginatedItems.value[0]?.path || ''
    }
    queueThumbnails()
}, { deep: true })

</script>

<style scoped>
.drive-page {
  padding: 20px;
}

.drive-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.drive-header-tools {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
}

.header-remote-select {
  width: 220px;
}

.header-remote-select :deep(.el-select__wrapper) {
  min-height: 38px;
  border-radius: 10px;
  background: #f8fafc;
  box-shadow: none;
  border: 1px solid #dbeafe;
}

.header-usage {
  display: flex;
  align-items: center;
  gap: 8px;
  padding: 7px 10px;
  border-radius: 10px;
  background: linear-gradient(135deg, #f8fafc 0%, #eef6ff 100%);
  border: 1px solid #dbeafe;
}

.header-usage-name {
  font-size: 12px;
  font-weight: 600;
  color: #0f172a;
}

.header-usage-text {
  font-size: 12px;
  color: #64748b;
  white-space: nowrap;
}

.drive-topbar {
  margin-bottom: 12px;
}

.drive-controls {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 10px 12px;
  border-radius: 12px;
  background: #f8fafc;
  border: 1px solid #e2e8f0;
}

.drive-breadcrumb-card {
  flex: 1;
  min-width: 240px;
}

.drive-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
}

.view-mode-toggle :deep(.el-button) {
  border-radius: 10px;
}

.sort-select {
  width: 152px;
}

.search-input {
  width: 260px;
}

.remote-option {
  display: flex;
  flex-direction: column;
  gap: 4px;
  padding: 2px 0;
}

.remote-option-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
}

.remote-option-name {
  font-size: 13px;
  font-weight: 600;
  color: #0f172a;
}

.remote-option-meta {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 11px;
  color: #64748b;
}

.remote-option-percent {
  padding: 1px 6px;
  border-radius: 999px;
  background: #dbeafe;
  color: #1d4ed8;
  font-weight: 600;
}

.file-name {
  display: flex;
  align-items: center;
}

.el-breadcrumb :deep(.el-breadcrumb__item) {
  cursor: pointer;
}

.el-breadcrumb :deep(.el-breadcrumb__inner):hover {
  color: var(--el-color-primary);
}

.tg-drive-shell {
  display: grid;
  grid-template-columns: 220px minmax(0, 1fr) 320px;
  gap: 16px;
  margin-top: 18px;
  align-items: start;
}

.tg-filter-rail {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
}

.tg-filter-pill {
  appearance: none;
  width: 100%;
  padding: 14px 16px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  text-align: left;
  transition: all 0.2s ease;
}

.tg-filter-pill:hover,
.tg-filter-pill.is-active {
  border-color: #bfdbfe;
  box-shadow: 0 12px 30px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
}

.tg-filter-pill.is-active {
  background: linear-gradient(180deg, #eff6ff 0%, #dbeafe 100%);
}

.tg-filter-pill-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  font-size: 14px;
  font-weight: 700;
  color: #0f172a;
}

.tg-filter-pill-count {
  color: #2563eb;
}

.tg-filter-pill-desc {
  display: block;
  margin-top: 6px;
  font-size: 12px;
  line-height: 1.5;
  color: #64748b;
}

.tg-drive-main {
  min-width: 0;
}

.tg-stream-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  margin-bottom: 14px;
}

.tg-stream-title {
  font-size: 18px;
  font-weight: 800;
  color: #0f172a;
}

.tg-stream-subtitle {
  margin-top: 4px;
  font-size: 12px;
  color: #64748b;
}

.tg-stream-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tg-file-row {
  display: grid;
  grid-template-columns: 56px minmax(0, 1fr) 180px;
  gap: 14px;
  padding: 14px 16px;
  border-radius: 18px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  transition: all 0.2s ease;
}

.tg-file-row:hover,
.tg-file-row.is-active {
  border-color: #bfdbfe;
  box-shadow: 0 16px 32px rgba(59, 130, 246, 0.10);
}

.tg-file-row.is-active {
  background: linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%);
}

.tg-file-avatar {
  width: 56px;
  height: 56px;
  border-radius: 18px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #e0e7ff 0%, #dbeafe 100%);
  color: #2563eb;
  overflow: hidden;
}

.tg-file-thumb {
  width: 100%;
  height: 100%;
}

.tg-file-thumb-fallback {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #f1f5f9 0%, #dbeafe 100%);
  color: #2563eb;
}

.tg-file-thumb-fallback.is-video {
  background: linear-gradient(135deg, #dbeafe 0%, #bfdbfe 100%);
}

.tg-file-body {
  min-width: 0;
}

.tg-file-title-row {
  display: flex;
  align-items: center;
  gap: 10px;
}

.tg-file-title {
  min-width: 0;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.tg-file-meta {
  margin-top: 6px;
  font-size: 13px;
  color: #475569;
}

.tg-file-path {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tg-file-trailing {
  display: flex;
  flex-direction: column;
  align-items: flex-end;
  justify-content: space-between;
  gap: 10px;
}

.tg-file-date {
  font-size: 12px;
  color: #64748b;
  text-align: right;
}

.tg-file-actions {
  display: flex;
  align-items: center;
  gap: 10px;
  flex-wrap: wrap;
  justify-content: flex-end;
}

.tg-inspector {
  position: sticky;
  top: 0;
  padding: 18px;
  border-radius: 22px;
  border: 1px solid #dbeafe;
  background: linear-gradient(180deg, #ffffff 0%, #f8fbff 100%);
  box-shadow: 0 18px 36px rgba(148, 163, 184, 0.14);
}

.tg-inspector-preview {
  height: 220px;
  border-radius: 22px;
  background: linear-gradient(135deg, #eff6ff 0%, #e2e8f0 100%);
  display: flex;
  align-items: center;
  justify-content: center;
  overflow: hidden;
  color: #2563eb;
  cursor: pointer;
}

.tg-inspector-image {
  width: 100%;
  height: 100%;
}

.tg-inspector-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  width: 100%;
  height: 100%;
}

.tg-inspector-fallback.is-video {
  background: linear-gradient(135deg, #dbeafe 0%, #c7d2fe 100%);
}

.tg-inspector-title {
  margin-top: 18px;
  font-size: 20px;
  font-weight: 800;
  color: #0f172a;
  word-break: break-word;
}

.tg-inspector-subtitle {
  margin-top: 8px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.tg-inspector-actions {
  display: flex;
  flex-direction: column;
  gap: 10px;
  margin-top: 18px;
}

.tg-inspector-meta {
  margin-top: 20px;
  padding-top: 18px;
  border-top: 1px solid #e2e8f0;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tg-inspector-meta-row {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.tg-inspector-meta-row span:first-child {
  color: #94a3b8;
}

.tg-inspector-meta-row span:last-child {
  color: #0f172a;
  word-break: break-word;
}

.tg-caption-row span:last-child {
  font-style: italic;
  color: #475569;
  line-height: 1.5;
}

.pagination-container {
  display: flex;
  justify-content: flex-end;
  margin-top: 20px;
}

/* 网格视图样式 */
.grid-view {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(160px, 1fr));
  gap: 16px;
  margin-top: 20px;
  padding: 8px;
}

.grid-item {
  border: 1px solid #e5e7eb;
  border-radius: 8px;
  padding: 12px;
  cursor: pointer;
  transition: all 0.3s;
  background: white;
}

.grid-item:hover {
  border-color: var(--el-color-primary);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-2px);
}

.grid-item-preview {
  width: 100%;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
  border-radius: 6px;
  overflow: hidden;
  position: relative;
}

.grid-icon {
  color: #909399;
}

.grid-thumbnail {
  width: 100%;
  height: 100%;
}

.image-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f5f7fa;
}

.video-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.video-placeholder .el-icon {
  color: white;
}

.grid-video {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
}

.grid-video .grid-thumbnail {
  width: 100%;
  height: 100%;
}

.grid-video .grid-icon {
  color: white;
}

.video-badge {
  position: absolute;
  bottom: 8px;
  right: 8px;
  background: rgba(0, 0, 0, 0.7);
  color: white;
  padding: 2px 8px;
  border-radius: 4px;
  font-size: 12px;
}

.grid-item-name {
  margin-top: 8px;
  font-size: 14px;
  text-align: center;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.grid-item-info {
  margin-top: 4px;
  display: flex;
  justify-content: space-between;
  align-items: center;
  min-height: 24px;
}

.grid-item-size {
  font-size: 12px;
  color: #909399;
}

.grid-item-actions {
  display: flex;
  gap: 4px;
  opacity: 0;
  transition: opacity 0.2s;
}

.grid-item:hover .grid-item-actions {
  opacity: 1;
}

.video-container {
  display: flex;
  justify-content: center;
  align-items: center;
  min-height: 420px;
  background: #000;
  border-radius: 4px;
  overflow: hidden;
}

.preview-loading-card {
  width: min(560px, 100%);
  padding: 28px;
  border-radius: 18px;
  background: linear-gradient(180deg, rgba(15, 23, 42, 0.96), rgba(30, 41, 59, 0.92));
  color: #e2e8f0;
}

.preview-loading-title {
  font-size: 24px;
  font-weight: 700;
}

.preview-loading-subtitle {
  margin-top: 8px;
  margin-bottom: 20px;
  color: #94a3b8;
  font-size: 14px;
  line-height: 1.6;
}

.preview-loading-meta {
  margin-top: 12px;
  color: #cbd5e1;
  font-size: 13px;
}

:deep(.drive-remote-popper .el-select-dropdown__item) {
  height: auto;
  min-height: 52px;
  padding-top: 6px;
  padding-bottom: 6px;
  line-height: 1.4;
}

@media (max-width: 960px) {
  .tg-drive-shell {
    grid-template-columns: 1fr;
  }

  .tg-filter-rail,
  .tg-inspector {
    position: static;
  }

  .tg-stream-header,
  .tg-file-row {
    display: flex;
    flex-direction: column;
    align-items: stretch;
  }

  .tg-file-trailing {
    align-items: flex-start;
  }

  .drive-actions {
    width: 100%;
  }

  .header-remote-select {
    width: 100%;
  }

  .sort-select,
  .search-input {
    width: 100%;
  }
}
</style>
