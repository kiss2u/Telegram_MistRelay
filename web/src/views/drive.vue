<template>
  <div class="drive-page">
    <el-card shadow="hover">
      <template #header>
        <div class="drive-header">
          <h2>我的网盘</h2>
        </div>
      </template>

      <!-- Remote 选择和路径导航 -->
      <div class="drive-controls">
        <el-select
          v-model="currentRemote"
          @change="handleRemoteChange"
          placeholder="选择云存储"
          style="width: 200px"
        >
          <el-option
            v-for="remote in availableRemotes"
            :key="remote.name"
            :label="`${remote.name} (${remote.type})`"
            :value="remote.name"
          />
        </el-select>

        <el-breadcrumb separator="/" style="margin-left: 20px; flex: 1">
          <el-breadcrumb-item @click="navigateToPath('/')">
            <el-icon><HomeFilled /></el-icon>
            根目录
          </el-breadcrumb-item>
          <el-breadcrumb-item
            v-for="(segment, index) in pathSegments"
            :key="index"
            @click="navigateToSegment(index)"
          >
            {{ segment }}
          </el-breadcrumb-item>
        </el-breadcrumb>

        <el-button-group style="margin-right: 10px">
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
          style="width: 140px; margin-right: 10px"
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


        <el-input
          v-model="searchKeyword"
          placeholder="搜索文件名"
          clearable
          style="width: 250px"
          :prefix-icon="Search"
        />
      </div>

      <!-- 列表视图 -->
      <el-table
        v-if="viewMode === 'list'"
        :data="paginatedItems"
        v-loading="loading"
        style="width: 100%; margin-top: 20px"
        @row-click="handleRowClick"
        :row-style="{ cursor: 'pointer' }"
      >
        <el-table-column label="名称" min-width="200">
          <template #default="{ row }">
            <div class="file-name">
              <el-icon :size="18" style="margin-right: 8px">
                <Folder v-if="row.isDir" />
                <Picture v-else-if="isImage(row.name)" />
                <VideoPlay v-else-if="isVideo(row.name)" />
                <Document v-else />
              </el-icon>
              {{ row.name }}
            </div>
          </template>
        </el-table-column>
        <el-table-column prop="size" label="大小" width="120">
          <template #default="{ row }">
            {{ row.isDir ? '-' : formatBytes(row.size) }}
          </template>
        </el-table-column>
        <el-table-column prop="modTime" label="修改时间" width="180">
          <template #default="{ row }">
            {{ formatDate(row.modTime) }}
          </template>
        </el-table-column>
        <el-table-column label="操作" width="150" align="center">
          <template #default="{ row }">
            <el-button-group>
              <el-button
                v-if="!row.isDir" 
                type="primary" 
                link 
                :icon="Download"
                @click.stop="handleDownload(row)"
              />
              <el-button 
                type="danger" 
                link 
                :icon="Delete"
                @click.stop="handleDelete(row)"
              />
            </el-button-group>
          </template>
        </el-table-column>
      </el-table>

      <!-- 网格视图 -->
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

      <!-- 分页 -->
      <div class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[20, 50, 100, 200]"
          :total="filteredItems.length"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!loading && items.length === 0" description="此目录为空" />
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
        <VideoPlayer 
          v-if="showPreview && previewType === 'video'"
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
import { HomeFilled, Document, Folder, Search, List, Grid, Picture, VideoPlay, Sort, Close, Download, Delete } from '@element-plus/icons-vue'
import { getRcloneRemotes, browseDrive, getThumbnail, deleteFile, type RcloneRemote, type DriveItem } from '@/api'
import VideoPlayer from '@/components/VideoPlayer.vue'

const availableRemotes = ref<RcloneRemote[]>([])
const currentRemote = ref('')
const currentPath = ref('/')
const items = ref<DriveItem[]>([])
const loading = ref(false)

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

// 计算属性
const pathSegments = computed(() => {
  const path = currentPath.value
  if (path === '/') return []
  return path.split('/').filter(Boolean)
})

const filteredItems = computed(() => {
  let result = items.value.slice()
  
  // 搜索过滤
  if (searchKeyword.value) {
    const keyword = searchKeyword.value.toLowerCase()
    result = result.filter(item => item.name.toLowerCase().includes(keyword))
  }
  
  // 排序:目录在前,文件在后, 然后根据选择的排序方式排序
  result.sort((a, b) => {
    // 始终让目录排在前面
    if (a.isDir !== b.isDir) {
      return a.isDir ? -1 : 1
    }
    
    // 如果都是目录或都是文件，则应用排序规则
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
  const start = (currentPage.value - 1) * pageSize.value
  const end = start + pageSize.value
  return filteredItems.value.slice(start, end)
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
    if (response.success && response.remotes) {
      availableRemotes.value = response.remotes
      if (response.remotes.length > 0 && !currentRemote.value) {
        currentRemote.value = response.remotes[0].name
      }
    }
  } catch (err) {
    console.error('加载 remotes 失败:', err)
    ElMessage.error('加载云存储列表失败')
  }
}

// 浏览目录
async function browse() {
  if (!currentRemote.value) return

  loading.value = true
  try {
    const response = await browseDrive(currentRemote.value, currentPath.value)
    if (response.success && response.items) {
      items.value = response.items
      // 重置分页
      currentPage.value = 1
    } else {
      ElMessage.error(response.error || '获取文件列表失败')
      items.value = []
    }
  } catch (err: any) {
    console.error('浏览失败:', err)
    ElMessage.error(err.message || '获取文件列表失败')
    items.value = []
  } finally {
    loading.value = false
  }
}

// Remote 改变
function handleRemoteChange() {
  currentPath.value = '/'
  browse()
}

// 下载文件
function handleDownload(item: DriveItem) {
  if (item.isDir) return
  
  const token = localStorage.getItem('token') || ''
  const protocol = window.location.protocol
  const host = window.location.host
  const url = `${protocol}//${host}/api/rclone/file?remote=${currentRemote.value}&path=${encodeURIComponent(item.path)}&download=true&token=${encodeURIComponent(token)}`
  
  window.open(url, '_blank')
}

// 删除文件
function handleDelete(item: DriveItem) {
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

// 点击行
function handleRowClick(row: DriveItem) {
  if (row.isDir) {
    // 进入目录
    navigateToPath(row.path)
  } else {
    // 预览文件
    if (isImage(row.name)) {
      previewType.value = 'image'
      previewItem.value = row
      const token = localStorage.getItem('token') || ''
      const protocol = window.location.protocol
      const host = window.location.host
      previewUrl.value = `${protocol}//${host}/api/rclone/file?remote=${currentRemote.value}&path=${encodeURIComponent(row.path)}&token=${encodeURIComponent(token)}`
      showPreview.value = true
    } else if (isVideo(row.name)) {
      previewType.value = 'video'
      previewItem.value = row
      const token = localStorage.getItem('token') || ''
      const protocol = window.location.protocol
      const host = window.location.host
      previewUrl.value = `${protocol}//${host}/api/rclone/file?remote=${currentRemote.value}&path=${encodeURIComponent(row.path)}&token=${encodeURIComponent(token)}`
      showPreview.value = true
    } else {
      ElMessage.info('暂不支持预览此类型文件')
    }
  }
}

// 关闭预览
function closePreview() {
  showPreview.value = false
  previewItem.value = null
  previewUrl.value = ''
  previewType.value = 'unknown'
}

// 导航到路径
function navigateToPath(path: string) {
  currentPath.value = path || '/'
  browse()
}

// 导航到面包屑某一段
function navigateToSegment(index: number) {
  const segments = pathSegments.value.slice(0, index + 1)
  navigateToPath('/' + segments.join('/'))
}

// 格式化文件大小
function formatBytes(bytes: number | undefined): string {
  if (!bytes || bytes === 0) return '0 B'
  const k = 1024
  const sizes = ['B', 'KB', 'MB', 'GB', 'TB']
  const i = Math.floor(Math.log(bytes) / Math.log(k))
  return parseFloat((bytes / Math.pow(k, i)).toFixed(2)) + ' ' + sizes[i]
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
    browse()
  }
})

// 监听视图模式变化
watch(viewMode, (newMode) => {
  if (newMode === 'grid') {
    queueThumbnails()
  }
})

// 监听分页数据变化
watch(paginatedItems, () => {
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
}

.drive-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 600;
}

.drive-controls {
  display: flex;
  align-items: center;
  margin-bottom: 20px;
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
  background: #000;
  border-radius: 4px;
  overflow: hidden;
}
</style>
