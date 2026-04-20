<template>
  <div class="drive-page" v-loading="previewLoading">
    <el-card shadow="hover">
      <template #header>
        <div class="drive-header">
          <div class="drive-header-tools">
            <div class="header-usage">
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
            </div>
          </div>
        </div>
      </template>

      <div class="drive-topbar">
        <div class="drive-controls">
          <el-button
            class="drive-nav-button"
            :icon="ArrowLeft"
            :disabled="!canNavigateUp"
            @click="navigateUp"
          >
            {{ currentTelegramGroupId ? '返回列表' : '返回上级' }}
          </el-button>

          <div class="drive-breadcrumb-card">
              <el-breadcrumb separator="/">
                <el-breadcrumb-item @click="navigateToPath('/')">
                  <el-icon><HomeFilled /></el-icon>
                  Telegram 频道
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

            <el-button plain @click="inspectorVisible = !inspectorVisible">
              {{ inspectorVisible ? '隐藏详情' : '显示详情' }}
            </el-button>

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
          </div>
        </div>
      </div>

      <div
        class="tg-drive-shell"
        :class="{ 'is-inspector-hidden': !inspectorVisible }"
        v-loading="loading"
      >
        <aside class="tg-filter-rail">
          <div class="tg-rail-summary">
            <div class="tg-rail-summary-label">我的网盘</div>
            <div class="tg-rail-summary-size">
              {{ telegramUsage ? formatBytes(telegramUsage.total_size) : '读取中...' }}
            </div>
            <div class="tg-rail-summary-meta">
              {{ telegramUsage ? `${formatCount(telegramUsage.total_count)} 个文件` : '正在同步统计信息' }}
            </div>
            <div class="tg-rail-summary-tags">
              <span class="tg-rail-summary-tag">在线播放</span>
              <span class="tg-rail-summary-tag">本地缓存</span>
            </div>
          </div>

          <div class="tg-rail-section">
            <div class="tg-rail-section-head">
              <span class="tg-rail-section-title">浏览</span>
              <span class="tg-rail-section-note">固定入口</span>
            </div>

            <button
              v-for="filter in quickFilterOptions"
              :key="filter.key"
              class="tg-filter-pill"
              :class="{ 'is-active': currentFilter === filter.key }"
              @click="currentFilter = filter.key"
            >
              <span class="tg-filter-pill-head">
                <span class="tg-filter-pill-title">
                  <el-icon class="tg-filter-pill-icon"><component :is="filter.icon" /></el-icon>
                  <span>{{ filter.label }}</span>
                </span>
                <span class="tg-filter-pill-count">{{ filter.count }}</span>
              </span>
              <span class="tg-filter-pill-desc">{{ filter.description }}</span>
            </button>
          </div>

          <div class="tg-rail-section">
            <div class="tg-rail-section-head">
              <span class="tg-rail-section-title">智能视图</span>
              <span class="tg-rail-section-note">PikPak 风格</span>
            </div>

            <button
              v-for="option in surfaceViewOptions"
              :key="option.key"
              class="tg-rail-compact"
              :class="{ 'is-active': surfaceView === option.key }"
              @click="surfaceView = option.key"
            >
              <span class="tg-rail-compact-mark">{{ option.short }}</span>
              <span class="tg-rail-compact-body">
                <span class="tg-rail-compact-title">{{ option.label }}</span>
                <span class="tg-rail-compact-desc">{{ option.description }}</span>
              </span>
              <span class="tg-rail-compact-count">{{ option.count }}</span>
            </button>
          </div>
        </aside>

        <section
          ref="driveMainRef"
          class="tg-drive-main"
          tabindex="0"
        >
          <div class="tg-stream-header">
            <div class="tg-stream-header-main">
              <div class="tg-stream-title">文件流</div>
              <div class="tg-stream-subtitle">
                Telegram 频道 · {{ activeQuickFilter?.label || '全部' }} · {{ activeSurfaceView?.label || '全部流' }} · {{ visibleItemCount }} 项
              </div>
              <div class="tg-stream-search">
                <el-input
                  v-model="searchInput"
                  placeholder="搜索文件名、媒体组标题或说明"
                  clearable
                  class="tg-stream-search-input"
                  :prefix-icon="Search"
                />
              </div>
              <div class="tg-stream-active-filters">
                <span class="tg-stream-filter-chip">
                  {{ activeQuickFilter?.label || '全部' }}
                </span>
                <span class="tg-stream-filter-chip is-muted">
                  {{ activeSurfaceView?.label || '全部流' }}
                </span>
                <span v-if="currentGroupMetaInfo" class="tg-stream-filter-chip is-soft">
                  媒体组合集
                </span>
              </div>
            </div>
            <div class="tg-stream-header-side">
              <el-tag round effect="plain">
                单击选择，双击打开，右键操作
              </el-tag>
              <el-tag round effect="plain" type="info">
                {{ currentGroupMetaInfo ? '合集详情视图' : 'PikPak 风格工作区' }}
              </el-tag>
            </div>
          </div>

          <div v-if="currentGroupMetaInfo" class="tg-group-hero">
            <div class="tg-group-hero-collage">
              <div
                v-for="previewPath in currentGroupPreviewPaths"
                :key="previewPath"
                class="tg-group-hero-tile"
              >
                <el-image
                  :src="getThumbnailUrlByPath(previewPath)"
                  fit="cover"
                  class="tg-group-hero-image"
                >
                  <template #error>
                    <div class="tg-group-hero-fallback">
                      <el-icon :size="18"><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
              </div>
              <div
                v-if="currentGroupPreviewPaths.length === 0"
                class="tg-group-hero-empty"
              >
                <el-icon :size="34"><Folder /></el-icon>
              </div>
            </div>

            <div class="tg-group-hero-body">
              <div class="tg-group-hero-eyebrow">媒体组合集</div>
              <div class="tg-group-hero-title">{{ currentGroupMetaInfo.title }}</div>
              <div class="tg-group-hero-description">{{ currentGroupDescription }}</div>
              <div class="tg-group-hero-stats">
                <div class="tg-group-hero-stat">
                  <span>文件</span>
                  <strong>{{ currentGroupMetaInfo.count }}</strong>
                </div>
                <div class="tg-group-hero-stat">
                  <span>总大小</span>
                  <strong>{{ formatBytes(currentGroupMetaInfo.size) }}</strong>
                </div>
                <div class="tg-group-hero-stat">
                  <span>内容</span>
                  <strong>{{ currentGroupSecondaryLabel }}</strong>
                </div>
                <div class="tg-group-hero-stat">
                  <span>更新</span>
                  <strong>{{ formatRelativeTime(currentGroupMetaInfo.modTime) }}</strong>
                </div>
              </div>
            </div>
          </div>

          <div v-if="selectedCount > 0" class="tg-selection-bar">
            <div class="tg-selection-summary">
              已选 {{ selectedCount }} 项
              <span v-if="selectedFileCount || selectedGroupCount" class="tg-selection-detail">
                {{ selectedFileCount }} 个文件<span v-if="selectedGroupCount"> · {{ selectedGroupCount }} 个媒体组</span>
              </span>
            </div>
            <div class="tg-selection-actions">
              <el-button size="small" @click="openSelectedItem" :disabled="selectedCount !== 1">
                打开
              </el-button>
              <el-button size="small" @click="handleDownloadSelected" :disabled="selectedFileCount === 0">
                批量下载
              </el-button>
              <el-button size="small" type="danger" plain @click="handleDeleteSelected">
                批量删除
              </el-button>
              <el-button size="small" @click="clearSelection">
                清除选择
              </el-button>
            </div>
          </div>

          <div v-if="viewMode === 'list'" class="tg-stream-list">
            <div class="tg-list-header">
              <button class="tg-list-header-cell is-name" @click="toggleSort('name')">
                名称
                <span class="tg-list-header-sort">{{ getSortIndicator('name') }}</span>
              </button>
              <div class="tg-list-header-cell is-description">说明 / 内容</div>
              <div class="tg-list-header-cell is-size">大小</div>
              <button class="tg-list-header-cell is-time" @click="toggleSort('time')">
                更新时间
                <span class="tg-list-header-sort">{{ getSortIndicator('time') }}</span>
              </button>
              <div class="tg-list-header-cell is-actions">操作</div>
            </div>

            <div
              v-for="item in paginatedItems"
              :key="item.path"
              class="tg-file-row"
              :class="{ 'is-active': isSelected(item.path) }"
              @click="handleItemClick(item, $event)"
              @dblclick="handleItemDoubleClick(item)"
              @contextmenu.prevent="handleItemContextMenu(item, $event)"
            >
              <div class="tg-file-primary">
                <div class="tg-file-avatar">
                  <div v-if="item.isDir" class="tg-group-stack">
                    <div
                      v-for="previewPath in getTelegramGroupPreviewPaths(item)"
                      :key="previewPath"
                      class="tg-group-stack-tile"
                    >
                      <el-image
                        :src="getThumbnailUrlByPath(previewPath)"
                        fit="cover"
                        class="tg-group-stack-image"
                      >
                        <template #error>
                          <div class="tg-group-stack-fallback">
                            <el-icon :size="14"><Picture /></el-icon>
                          </div>
                        </template>
                      </el-image>
                    </div>
                    <div
                      v-if="getTelegramGroupPreviewPaths(item).length === 0"
                      class="tg-group-stack-empty"
                    >
                      <el-icon :size="22"><Folder /></el-icon>
                    </div>
                  </div>
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
                    <el-tag size="small" effect="plain" round class="tg-file-type-tag">
                      {{ getItemTypeLabel(item) }}
                    </el-tag>
                  </div>
                  <div class="tg-file-primary-meta">
                    {{ item.isDir ? '媒体组合集' : 'Telegram 频道文件' }}
                  </div>
                </div>
              </div>

              <div class="tg-file-description">
                <div class="tg-file-description-main" :title="getItemDescriptionLine(item)">
                  {{ getItemDescriptionLine(item) }}
                </div>
                <div class="tg-file-description-sub" :title="getItemDescriptionSubline(item)">
                  {{ getItemDescriptionSubline(item) }}
                </div>
              </div>

              <div class="tg-file-size">
                {{ getItemSizeDisplay(item) }}
              </div>

              <div class="tg-file-time">
                <div class="tg-file-time-main">{{ formatDate(item.modTime) }}</div>
                <div class="tg-file-time-sub">{{ formatRelativeTime(item.modTime) }}</div>
              </div>

              <div class="tg-file-actions-col">
                <div class="tg-file-actions">
                  <el-button link type="primary" @click.stop="handleItemAction(item, 'open')">
                    {{ item.isDir ? '进入' : '打开' }}
                  </el-button>
                  <el-button
                    v-if="!item.isDir"
                    link
                    @click.stop="handleItemAction(item, 'download')"
                  >
                    下载
                  </el-button>
                  <el-button link type="danger" @click.stop="handleItemAction(item, 'delete')">
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
              :class="{ 'is-active': isSelected(item.path) }"
              @click="handleItemClick(item, $event)"
              @dblclick.stop="handleItemDoubleClick(item)"
              @contextmenu.prevent="handleItemContextMenu(item, $event)"
            >
              <div class="grid-item-preview">
                <div v-if="item.isDir" class="grid-group-collage">
                  <div
                    v-for="previewPath in getTelegramGroupPreviewPaths(item)"
                    :key="previewPath"
                    class="grid-group-collage-tile"
                  >
                    <el-image
                      :src="getThumbnailUrlByPath(previewPath)"
                      fit="cover"
                      class="grid-group-collage-image"
                      lazy
                    >
                      <template #error>
                        <div class="grid-group-collage-fallback">
                          <el-icon :size="24"><Picture /></el-icon>
                        </div>
                      </template>
                    </el-image>
                  </div>
                  <div
                    v-if="getTelegramGroupPreviewPaths(item).length === 0"
                    class="grid-group-collage-empty"
                  >
                    <el-icon :size="42"><Folder /></el-icon>
                  </div>
                  <div class="grid-group-badge">{{ getTelegramGroupSecondaryLabel(item) }}</div>
                </div>
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
                    @click.stop="handleItemAction(item, 'download')"
                  />
                  <el-button
                    circle
                    size="small"
                    type="danger"
                    :icon="Delete"
                    @click.stop="handleItemAction(item, 'delete')"
                  />
                </div>
              </div>
            </div>
          </div>
        </section>

        <aside class="tg-inspector" v-if="inspectorVisible && selectedItem">
          <div class="tg-inspector-preview" @click="handleRowClick(selectedItem)">
            <div v-if="selectedItem.isDir" class="tg-inspector-group-collage">
              <div
                v-for="previewPath in getTelegramGroupPreviewPaths(selectedItem)"
                :key="previewPath"
                class="tg-inspector-group-tile"
              >
                <el-image
                  :src="getThumbnailUrlByPath(previewPath)"
                  fit="cover"
                  class="tg-inspector-group-image"
                >
                  <template #error>
                    <div class="tg-inspector-group-fallback">
                      <el-icon :size="20"><Picture /></el-icon>
                    </div>
                  </template>
                </el-image>
              </div>
              <div
                v-if="getTelegramGroupPreviewPaths(selectedItem).length === 0"
                class="tg-inspector-group-empty"
              >
                <el-icon :size="54">
                  <Folder />
                </el-icon>
              </div>
            </div>
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

          <div class="tg-inspector-title" :title="selectedItem.name">{{ selectedItem.name }}</div>
          <div class="tg-inspector-subtitle">{{ getItemMetaLine(selectedItem) }}</div>

          <div class="tg-inspector-actions">
            <el-button type="primary" @click="handleRowClick(selectedItem)">
              {{ selectedItem.isDir ? '进入文件夹' : '打开预览' }}
            </el-button>
            <el-button v-if="!selectedItem.isDir" @click="handleDownload(selectedItem)">
              下载到本地
            </el-button>
            <el-button type="danger" plain @click="handleDelete(selectedItem)">
              {{ isTelegramMode && selectedItem.isDir ? '删除媒体组' : '删除' }}
            </el-button>
          </div>

          <div class="tg-inspector-meta">
            <template v-if="!selectedItem.isDir && telegramItemMeta[selectedItem.path]">
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
            <template v-if="selectedItem.isDir && telegramGroupMeta[selectedItem.path]">
              <div class="tg-inspector-meta-row">
                <span>媒体组</span>
                <span>{{ telegramGroupMeta[selectedItem.path].count }} 个文件</span>
              </div>
              <div class="tg-inspector-meta-row">
                <span>组大小</span>
                <span>{{ formatBytes(telegramGroupMeta[selectedItem.path].size) }}</span>
              </div>
            </template>
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
              <span>Telegram 频道</span>
            </div>
          </div>
        </aside>
      </div>

      <!-- 分页 -->
      <div v-if="showPagination" class="pagination-container">
        <el-pagination
          v-model:current-page="currentPage"
          v-model:page-size="pageSize"
          :page-sizes="[10, 20, 50, 100, 200]"
          :total="paginationTotal"
          layout="total, sizes, prev, pager, next, jumper"
          background
        />
      </div>

      <!-- 空状态 -->
      <el-empty v-if="!loading && visibleItemCount === 0" description="此目录为空" />
    </el-card>

    <div
      v-if="contextMenu.visible"
      class="tg-context-menu"
      :style="contextMenuStyle"
      @contextmenu.prevent
    >
      <button class="tg-context-menu-item" @click="handleContextMenuAction('open')" :disabled="selectedCount !== 1">
        {{ selectedItem?.isDir ? '进入媒体组' : '打开预览' }}
      </button>
      <button class="tg-context-menu-item" @click="handleContextMenuAction('download')" :disabled="selectedFileCount === 0">
        {{ selectedCount > 1 ? '下载已选文件' : '下载到本地' }}
      </button>
      <button class="tg-context-menu-item is-danger" @click="handleContextMenuAction('delete')" :disabled="selectedCount === 0">
        {{ selectedCount > 1 ? '删除已选项' : '删除' }}
      </button>
      <div class="tg-context-menu-separator" />
      <button class="tg-context-menu-item" @click="handleContextMenuAction('selectAll')">
        全选当前页
      </button>
      <button class="tg-context-menu-item" @click="handleContextMenuAction('clearSelection')" :disabled="selectedCount === 0">
        清除选择
      </button>
    </div>

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
        />
      </div>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onBeforeUnmount, watch } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import { HomeFilled, Document, Folder, Search, List, Grid, Picture, VideoPlay, Sort, Download, Delete, RefreshRight, ArrowLeft } from '@element-plus/icons-vue'
import { getThumbnail, browseTelegram, getTelegramUsage, deleteTelegramItem, deleteTelegramGroup, clearTelegramMedia, type DriveItem, type TelegramMediaItem, type TelegramUsageStats } from '@/api'
import VideoPlayer from '@/components/VideoPlayer.vue'
import {
  cancelDesktopPreview,
  getDesktopTransferStatus,
  prepareDesktopPreviewFile,
  startDesktopPreviewStream,
  toDesktopAssetUrl,
  type DesktopTransferStatus,
} from '@/utils/desktop'
import { useDesktopDownloads } from '@/composables/useDesktopDownloads'
import { toAbsoluteServerUrl } from '@/utils/runtime'

const { startTrackedDesktopDownload } = useDesktopDownloads()

type QuickFilter = 'all' | 'folders' | 'videos' | 'images' | 'documents' | 'recent'
type SurfaceView = 'all' | 'recent' | 'groups' | 'singles' | 'large'
type SortField = 'name' | 'time'
type ContextAction = 'open' | 'download' | 'delete' | 'selectAll' | 'clearSelection'
type QuickFilterOption = {
  key: QuickFilter
  label: string
  description: string
  count: number
  icon: typeof HomeFilled
}
type SurfaceViewOption = {
  key: SurfaceView
  label: string
  short: string
  description: string
  count: number
}

const TELEGRAM_REMOTE_NAME = '__telegram__'
const DRIVE_PAGE_SIZE_STORAGE_KEY = 'mistrelay-drive-page-size'
const DRIVE_VIEW_MODE_STORAGE_KEY = 'mistrelay-drive-view-mode'
const DRIVE_INSPECTOR_STORAGE_KEY = 'mistrelay-drive-inspector-visible'

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
  previewPaths: string[]
  videoCount: number
  imageCount: number
}

const telegramItemMeta = ref<Record<string, TelegramItemMeta>>({})
const telegramGroupMeta = ref<Record<string, TelegramGroupMeta>>({})
const telegramTotal = ref(0)
const telegramUsage = ref<TelegramUsageStats | null>(null)
const loadingTelegramUsage = ref(false)

const isTelegramMode = computed(() => true)
const TELEGRAM_GROUP_PATH_PREFIX = '/__tg_group__/'

const currentRemote = ref(TELEGRAM_REMOTE_NAME)
const currentPath = ref('/')
const items = ref<DriveItem[]>([])
const loading = ref(false)
const currentFilter = ref<QuickFilter>('all')
const selectedItemPath = ref('')
const selectedPaths = ref<string[]>([])
const lastSelectedPath = ref('')
const driveMainRef = ref<HTMLElement | null>(null)
const inspectorVisible = ref(true)
const searchKeyword = ref('')
const searchInput = ref('')
const surfaceView = ref<SurfaceView>('all')
let searchDebounceTimer: number | null = null
const contextMenu = ref({
  visible: false,
  x: 0,
  y: 0,
})

// 搜索和分页
const currentPage = ref(1)
const pageSize = ref(readStoredPageSize())

// 视图模式
const viewMode = ref<'list' | 'grid'>(readStoredViewMode())

// 排序状态
const sortBy = ref<SortField>('time')
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
const currentTelegramGroupId = computed(() => (
  isTelegramMode.value && currentPath.value.startsWith(TELEGRAM_GROUP_PATH_PREFIX)
    ? currentPath.value.slice(TELEGRAM_GROUP_PATH_PREFIX.length)
    : null
))

const parentPath = computed(() => {
  if (isTelegramMode.value) {
    return currentTelegramGroupId.value ? '/' : null
  }

  const path = currentPath.value || '/'
  if (path === '/') return null

  const segments = path.split('/').filter(Boolean)
  if (segments.length <= 1) return '/'
  return `/${segments.slice(0, -1).join('/')}`
})

const canNavigateUp = computed(() => parentPath.value !== null)

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
  const u = telegramUsage.value
  return [
    { key: 'all' as QuickFilter, label: '全部', description: '频道中的所有媒体文件', count: u?.total_count || 0, icon: HomeFilled },
    { key: 'videos' as QuickFilter, label: '视频', description: '在线播放和本地缓存优先', count: u?.videos || 0, icon: VideoPlay },
    { key: 'images' as QuickFilter, label: '图片', description: '快速预览图片资源', count: u?.images || 0, icon: Picture },
    { key: 'documents' as QuickFilter, label: '文档', description: '压缩包、PDF 和普通文件', count: u?.documents || 0, icon: Document },
  ] satisfies QuickFilterOption[]
})

const activeQuickFilter = computed(() => (
  quickFilterOptions.value.find(item => item.key === currentFilter.value) || null
))

const telegramItemsByPath = computed(() => new Map(items.value.map(item => [item.path, item])))

const telegramVisibleItems = computed(() => {
  const groupId = currentTelegramGroupId.value
  if (groupId) {
    return items.value.filter(item => telegramItemMeta.value[item.path]?.mediaGroupId === groupId)
  }

  // In category views users expect real media files, not synthetic group folders.
  if (currentFilter.value !== 'all') {
    telegramGroupMeta.value = {}
    return items.value
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
      previewPaths: members
        .filter(member => isImage(member.name) || isVideo(member.name))
        .slice(0, 4)
        .map(member => member.path),
      videoCount: members.filter(member => isVideo(member.name)).length,
      imageCount: members.filter(member => isImage(member.name)).length,
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
  return telegramVisibleItems.value.filter(matchesSurfaceView)
})

const paginatedItems = computed(() => {
  return filteredItems.value
})

const surfaceViewOptions = computed(() => {
  const source = telegramVisibleItems.value
  return [
    { key: 'all' as SurfaceView, label: '全部流', short: '全', description: '当前筛选下的完整文件流', count: source.length },
    { key: 'recent' as SurfaceView, label: '最近', short: '近', description: '近 7 天新增或更新的内容', count: source.filter(item => isRecentItem(item)).length },
    { key: 'groups' as SurfaceView, label: '媒体组', short: '组', description: '多文件合集和相册视图', count: source.filter(item => item.isDir).length },
    { key: 'singles' as SurfaceView, label: '单文件', short: '单', description: '单个视频、图片和文档', count: source.filter(item => !item.isDir).length },
    { key: 'large' as SurfaceView, label: '大文件', short: '大', description: '100 MB 以上的单文件', count: source.filter(item => !item.isDir && (item.size || 0) >= 100 * 1024 * 1024).length },
  ] satisfies SurfaceViewOption[]
})

const activeSurfaceView = computed(() => (
  surfaceViewOptions.value.find(item => item.key === surfaceView.value) || null
))

const visibleItemCount = computed(() => filteredItems.value.length)
const paginationTotal = computed(() => (
  currentTelegramGroupId.value
    ? filteredItems.value.length
    : telegramTotal.value
))
const showPagination = computed(() => !isTelegramMode.value || !currentTelegramGroupId.value)

const selectedItem = computed(() => {
  return paginatedItems.value.find(item => item.path === selectedItemPath.value) || paginatedItems.value[0] || null
})

const selectedItems = computed(() => {
  const selectedSet = new Set(selectedPaths.value)
  return paginatedItems.value.filter(item => selectedSet.has(item.path))
})

const selectedCount = computed(() => selectedPaths.value.length)
const selectedFileCount = computed(() => selectedItems.value.filter(item => !item.isDir).length)
const selectedGroupCount = computed(() => selectedItems.value.filter(item => item.isDir).length)

const contextMenuStyle = computed(() => ({
  left: `${contextMenu.value.x}px`,
  top: `${contextMenu.value.y}px`,
}))

const currentGroupPath = computed(() => (
  currentTelegramGroupId.value ? `${TELEGRAM_GROUP_PATH_PREFIX}${currentTelegramGroupId.value}` : ''
))

const currentGroupMetaInfo = computed(() => (
  currentGroupPath.value ? telegramGroupMeta.value[currentGroupPath.value] || null : null
))

const currentGroupPreviewPaths = computed(() => (
  currentGroupMetaInfo.value?.previewPaths || []
))

const currentGroupSecondaryLabel = computed(() => {
  if (!currentGroupPath.value) return ''
  return getTelegramGroupSecondaryLabel({
    name: currentGroupMetaInfo.value?.title || '媒体组',
    path: currentGroupPath.value,
    size: currentGroupMetaInfo.value?.size || 0,
    mimeType: '',
    modTime: currentGroupMetaInfo.value?.modTime,
    isDir: true,
  })
})

const currentGroupDescription = computed(() => {
  if (!currentGroupMetaInfo.value) return ''
  const parts = [
    currentGroupSecondaryLabel.value,
    currentGroupMetaInfo.value.size > 0 ? formatBytes(currentGroupMetaInfo.value.size) : '',
    currentGroupMetaInfo.value.modTime ? formatDate(currentGroupMetaInfo.value.modTime) : '',
  ].filter(Boolean)
  return parts.join(' · ')
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

function isRecentItem(item: DriveItem): boolean {
  if (!item.modTime) return false
  const timestamp = new Date(item.modTime).getTime()
  if (Number.isNaN(timestamp)) return false
  return Date.now() - timestamp <= 7 * 24 * 60 * 60 * 1000
}

function matchesSurfaceView(item: DriveItem): boolean {
  switch (surfaceView.value) {
    case 'recent':
      return isRecentItem(item)
    case 'groups':
      return item.isDir
    case 'singles':
      return !item.isDir
    case 'large':
      return !item.isDir && (item.size || 0) >= 100 * 1024 * 1024
    default:
      return true
  }
}

function buildTelegramGroupTitle(mediaGroupId: string, members: DriveItem[]): string {
  const first = members[0]
  const firstMeta = first ? telegramItemMeta.value[first.path] : null
  const baseTitle = firstMeta?.caption?.trim() || first?.name || `媒体组 ${mediaGroupId.slice(-6)}`
  return baseTitle.replace(/\s+/g, ' ').trim()
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

function getItemDescriptionLine(item: DriveItem): string {
  if (item.isDir) {
    const group = telegramGroupMeta.value[item.path]
    if (!group) return '媒体组合集'
    return `${group.count} 个文件 · ${getTelegramGroupSecondaryLabel(item)}`
  }

  const meta = telegramItemMeta.value[item.path]
  return meta?.caption?.trim() || 'Telegram 频道文件'
}

function getItemDescriptionSubline(item: DriveItem): string {
  if (item.isDir) {
    const group = telegramGroupMeta.value[item.path]
    if (!group) return '进入后查看组内文件'
    return group.modTime ? `最后更新 ${formatDate(group.modTime)}` : '进入后查看组内文件'
  }

  const metaParts = [getItemMetaLine(item)]
  if (telegramItemMeta.value[item.path]?.messageId) {
    metaParts.push(`消息 ${telegramItemMeta.value[item.path].messageId}`)
  }
  return metaParts.join(' · ')
}

function getItemSizeDisplay(item: DriveItem): string {
  if (item.isDir) {
    const group = telegramGroupMeta.value[item.path]
    return formatBytes(group?.size || item.size || 0)
  }
  return formatBytes(item.size)
}

function getTelegramGroupPreviewPaths(item: DriveItem): string[] {
  return telegramGroupMeta.value[item.path]?.previewPaths || []
}

function getThumbnailUrlByPath(path: string): string {
  const item = telegramItemsByPath.value.get(path)
  if (!item) return ''
  return getThumbnailUrl(item)
}

function getTelegramGroupSecondaryLabel(item: DriveItem): string {
  const group = telegramGroupMeta.value[item.path]
  if (!group) return '媒体组'
  if (group.videoCount > 0 && group.imageCount > 0) {
    return `${group.videoCount} 视频 · ${group.imageCount} 图片`
  }
  if (group.videoCount > 0) {
    return `${group.videoCount} 个视频`
  }
  if (group.imageCount > 0) {
    return `${group.imageCount} 张图片`
  }
  return `${group.count} 个文件`
}

function selectItem(item: DriveItem) {
  selectSingleItem(item.path)
}

function readStoredPageSize(): number {
  const value = Number(window.localStorage.getItem(DRIVE_PAGE_SIZE_STORAGE_KEY) || '')
  return [10, 20, 50, 100, 200].includes(value) ? value : 50
}

function readStoredViewMode(): 'list' | 'grid' {
  return window.localStorage.getItem(DRIVE_VIEW_MODE_STORAGE_KEY) === 'grid' ? 'grid' : 'list'
}

function isSelected(path: string): boolean {
  return selectedPaths.value.includes(path)
}

function setSelectedPaths(paths: string[]) {
  const deduped = Array.from(new Set(paths))
  selectedPaths.value = deduped
  selectedItemPath.value = deduped[0] || ''
  if (deduped[0]) {
    lastSelectedPath.value = deduped[0]
  }
}

function selectSingleItem(path: string) {
  setSelectedPaths([path])
}

function clearSelection() {
  selectedPaths.value = []
  selectedItemPath.value = ''
}

function getItemByPath(path: string): DriveItem | undefined {
  return paginatedItems.value.find(item => item.path === path)
}

function selectRangeTo(path: string) {
  const anchorPath = lastSelectedPath.value || selectedPaths.value[0] || path
  const startIndex = paginatedItems.value.findIndex(item => item.path === anchorPath)
  const endIndex = paginatedItems.value.findIndex(item => item.path === path)
  if (startIndex === -1 || endIndex === -1) {
    selectSingleItem(path)
    return
  }

  const [from, to] = startIndex < endIndex ? [startIndex, endIndex] : [endIndex, startIndex]
  setSelectedPaths(paginatedItems.value.slice(from, to + 1).map(item => item.path))
}

function toggleItemSelection(path: string) {
  if (isSelected(path)) {
    const next = selectedPaths.value.filter(selectedPath => selectedPath !== path)
    setSelectedPaths(next)
  } else {
    setSelectedPaths([...selectedPaths.value, path])
  }
  lastSelectedPath.value = path
}

function selectAllVisible() {
  setSelectedPaths(paginatedItems.value.map(item => item.path))
}

function handleItemClick(item: DriveItem, event: MouseEvent) {
  hideContextMenu()

  if (event.shiftKey) {
    selectRangeTo(item.path)
  } else if (event.ctrlKey || event.metaKey) {
    toggleItemSelection(item.path)
  } else {
    selectSingleItem(item.path)
  }
}

function handleItemDoubleClick(item: DriveItem) {
  selectSingleItem(item.path)
  void handleRowClick(item)
}

function handleItemAction(item: DriveItem, action: 'open' | 'download' | 'delete') {
  selectSingleItem(item.path)
  if (action === 'open') {
    void handleRowClick(item)
    return
  }
  if (action === 'download') {
    void handleDownload(item)
    return
  }
  if (action === 'delete') {
    void handleDeleteSelected([item.path])
  }
}

function handleItemContextMenu(item: DriveItem, event: MouseEvent) {
  if (!isSelected(item.path)) {
    selectSingleItem(item.path)
  }

  contextMenu.value = {
    visible: true,
    x: event.clientX,
    y: event.clientY,
  }
}

function hideContextMenu() {
  if (!contextMenu.value.visible) return
  contextMenu.value.visible = false
}

function toggleSort(field: SortField) {
  if (sortBy.value === field) {
    sortDesc.value = !sortDesc.value
    return
  }
  sortBy.value = field
  sortDesc.value = field === 'time'
}

function getSortIndicator(field: SortField): string {
  if (sortBy.value !== field) return ''
  return sortDesc.value ? '↓' : '↑'
}

async function downloadItems(itemsToDownload: DriveItem[]): Promise<void> {
  if (itemsToDownload.length === 0) return

  let queuedCount = 0
  let skippedCount = 0

  for (const item of itemsToDownload) {
    if (item.isDir) continue
    const url = getTelegramDirectLink(item)
    const queued = await startTrackedDesktopDownload({
      sourceUrl: url,
      remote: 'telegram',
      remotePath: item.path,
      fileName: item.name,
      pathKey: `telegram:${item.path}`,
    })
    if (queued) {
      queuedCount += 1
    } else {
      skippedCount += 1
    }
  }

  if (queuedCount > 0 && skippedCount > 0) {
    ElMessage.success(`已加入下载 ${queuedCount} 项，${skippedCount} 项已在队列中`)
  } else if (queuedCount > 0) {
    ElMessage.success(`已加入下载 ${queuedCount} 项`)
  } else {
    ElMessage.info('所选文件已在本地下载队列中')
  }
}

function getSelectedOrProvidedItems(paths?: string[]): DriveItem[] {
  const targetPaths = paths ?? selectedPaths.value
  const targetSet = new Set(targetPaths)
  return paginatedItems.value.filter(item => targetSet.has(item.path))
}

async function handleDownloadSelected() {
  await downloadItems(getSelectedOrProvidedItems().filter(item => !item.isDir))
}

async function deleteItems(itemsToDelete: DriveItem[]): Promise<void> {
  if (itemsToDelete.length === 0) return

  const hasGroups = itemsToDelete.some(item => item.isDir)
  const label = itemsToDelete.length === 1
    ? `${itemsToDelete[0].isDir ? '媒体组' : '文件'} "${itemsToDelete[0].name}"`
    : `${itemsToDelete.length} 个项目`

  await ElMessageBox.confirm(
    `确定要删除 ${label} 吗？这会删除频道内对应消息，并清理相关记录。`,
    '确认删除',
    {
      confirmButtonText: '删除',
      cancelButtonText: '取消',
      type: 'warning',
    }
  )

  loading.value = true
  try {
    for (const item of itemsToDelete) {
      const mediaGroupId = item.isDir ? getTelegramGroupIdFromItem(item) : null
      const messageId = item.isDir ? null : telegramItemMeta.value[item.path]?.messageId

      if (item.isDir) {
        if (!mediaGroupId) {
          throw new Error(`媒体组 "${item.name}" 缺少分组标识`)
        }
        const response = await deleteTelegramGroup(mediaGroupId)
        if (!response.success) {
          throw new Error(response.error || `删除媒体组 "${item.name}" 失败`)
        }
        if (currentTelegramGroupId.value === mediaGroupId) {
          currentPath.value = '/'
        }
      } else {
        if (!messageId) {
          throw new Error(`文件 "${item.name}" 缺少消息 ID`)
        }
        const response = await deleteTelegramItem(messageId)
        if (!response.success) {
          throw new Error(response.error || `删除文件 "${item.name}" 失败`)
        }
      }
    }

    clearSelection()
    await refreshTelegramViewAfterMutation()
    ElMessage.success(
      itemsToDelete.length === 1
        ? `${hasGroups ? '媒体组' : '文件'}删除成功`
        : `已删除 ${itemsToDelete.length} 个项目`
    )
  } finally {
    loading.value = false
  }
}

function openSelectedItem() {
  const item = selectedItems.value[0]
  if (!item || selectedCount.value !== 1) return
  void handleRowClick(item)
}

async function handleDeleteSelected(paths?: string[]) {
  const itemsToDelete = getSelectedOrProvidedItems(paths)
  if (itemsToDelete.length === 0) return

  try {
    await deleteItems(itemsToDelete)
  } catch (err: any) {
    if (err !== 'cancel' && err !== 'close') {
      console.error('删除 tg 网盘项目失败:', err)
      ElMessage.error(err.message || '删除失败')
    }
  }
}

function handleContextMenuAction(action: ContextAction) {
  hideContextMenu()
  if (action === 'open') {
    openSelectedItem()
    return
  }
  if (action === 'download') {
    void handleDownloadSelected()
    return
  }
  if (action === 'delete') {
    void handleDeleteSelected()
    return
  }
  if (action === 'selectAll') {
    selectAllVisible()
    return
  }
  clearSelection()
}

function moveSelection(offset: number) {
  if (paginatedItems.value.length === 0) return

  const currentPath = selectedPaths.value[0] || paginatedItems.value[0]?.path
  const currentIndex = paginatedItems.value.findIndex(item => item.path === currentPath)
  const nextIndex = currentIndex === -1
    ? 0
    : Math.min(Math.max(currentIndex + offset, 0), paginatedItems.value.length - 1)

  const nextItem = paginatedItems.value[nextIndex]
  if (!nextItem) return
  selectSingleItem(nextItem.path)
}

function handleGlobalPointerDown(event: MouseEvent) {
  const target = event.target as Node | null
  if (target && driveMainRef.value?.contains(target)) return
  hideContextMenu()
}

function handleDriveKeydown(event: KeyboardEvent) {
  const target = event.target as HTMLElement | null
  if (target && ['INPUT', 'TEXTAREA'].includes(target.tagName)) {
    return
  }

  if ((event.ctrlKey || event.metaKey) && event.key.toLowerCase() === 'a') {
    event.preventDefault()
    selectAllVisible()
    return
  }

  if (event.key === 'Escape') {
    hideContextMenu()
    clearSelection()
    return
  }

  if (event.key === 'ArrowDown') {
    event.preventDefault()
    moveSelection(1)
    return
  }

  if (event.key === 'ArrowUp') {
    event.preventDefault()
    moveSelection(-1)
    return
  }

  if (event.key === 'Enter') {
    event.preventDefault()
    openSelectedItem()
    return
  }

  if (event.key === 'Delete' || event.key === 'Backspace') {
    if (selectedCount.value > 0) {
      event.preventDefault()
      void handleDeleteSelected()
    }
  }
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
      
      try {
        console.log('正在加载缩略图:', item.name)
        const response = await getThumbnail(currentRemote.value, item.path, 'telegram', currentPath.value, item.id || '')
        
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
  await browseTelegramChannel()
}

// 下载文件
async function handleDownload(item: DriveItem) {
  if (item.isDir) return
  selectSingleItem(item.path)
  await downloadItems([item])
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
  selectSingleItem(item.path)
  void handleDeleteSelected([item.path])
}

// 预览状态
const showPreview = ref(false)
const previewItem = ref<DriveItem | null>(null)
const previewType = ref<'image' | 'video' | 'unknown'>('unknown')
const previewUrl = ref('')
const previewLoading = ref(false)
const previewTransferStatus = ref<DesktopTransferStatus | null>(null)
const previewTransferId = ref('')
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
  return getTelegramDirectLink(row)
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
    remote: 'telegram',
    remotePath: row.path,
    fileName: row.name,
  })

  return toDesktopAssetUrl(result.localPath)
}

function sleep(ms: number): Promise<void> {
  return new Promise(resolve => window.setTimeout(resolve, ms))
}

async function cancelPreviewSession(transferId: string): Promise<void> {
  try {
    await cancelDesktopPreview(transferId)
  } catch (err) {
    console.error('释放本地预览会话失败:', err)
  }
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
      previewTransferId.value = ''
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
      previewTransferId.value = ''
      showPreview.value = true
      previewLoading.value = true
      const token = ++previewRequestToken
      try {
        const sourceUrl = getSourceUrlForItem(row)
        const session = await startDesktopPreviewStream({
          sourceUrl,
          remote: 'telegram',
          remotePath: row.path,
          fileName: row.name,
        })
        previewTransferId.value = session.transferId

        if (token !== previewRequestToken || !showPreview.value) {
          await cancelPreviewSession(session.transferId)
          return
        }

        await waitForPreviewReady(session.transferId, token)

        if (token !== previewRequestToken || !showPreview.value) {
          await cancelPreviewSession(session.transferId)
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
  const transferId = previewTransferId.value
  previewRequestToken += 1
  showPreview.value = false
  previewItem.value = null
  previewUrl.value = ''
  previewType.value = 'unknown'
  previewLoading.value = false
  previewTransferStatus.value = null
  previewTransferId.value = ''

  if (transferId) {
    void cancelPreviewSession(transferId)
  }
}

// 导航到路径
function navigateToPath(path: string) {
  currentPath.value = path || '/'
}

function navigateUp() {
  if (!parentPath.value) return
  navigateToPath(parentPath.value)
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
  inspectorVisible.value = window.localStorage.getItem(DRIVE_INSPECTOR_STORAGE_KEY) !== '0'
  window.addEventListener('keydown', handleDriveKeydown)
  window.addEventListener('pointerdown', handleGlobalPointerDown)
  await loadTelegramUsage()
  await browseTelegramChannel()
})

onBeforeUnmount(() => {
  if (searchDebounceTimer) {
    window.clearTimeout(searchDebounceTimer)
  }
  window.removeEventListener('keydown', handleDriveKeydown)
  window.removeEventListener('pointerdown', handleGlobalPointerDown)
})

// 监听视图模式变化
watch(viewMode, (newMode) => {
  window.localStorage.setItem(DRIVE_VIEW_MODE_STORAGE_KEY, newMode)
  if (newMode === 'grid') {
    queueThumbnails()
  }
})

watch(inspectorVisible, (value) => {
  window.localStorage.setItem(DRIVE_INSPECTOR_STORAGE_KEY, value ? '1' : '0')
})

watch(searchInput, (value) => {
  if (searchDebounceTimer) {
    window.clearTimeout(searchDebounceTimer)
  }
  searchDebounceTimer = window.setTimeout(() => {
    searchKeyword.value = value.trim()
  }, 280)
})

watch([currentFilter, searchKeyword], () => {
  hideContextMenu()
  clearSelection()
  currentPage.value = 1
  if (isTelegramMode.value) {
    browseTelegramChannel()
  }
})

watch([currentPage, pageSize], () => {
  window.localStorage.setItem(DRIVE_PAGE_SIZE_STORAGE_KEY, String(pageSize.value))
  hideContextMenu()
  clearSelection()
  if (isTelegramMode.value && !currentTelegramGroupId.value) {
    browseTelegramChannel()
  }
})

watch([sortBy, sortDesc], () => {
  hideContextMenu()
  clearSelection()
  if (isTelegramMode.value) {
    currentPage.value = 1
    browseTelegramChannel()
  }
})

watch(currentPath, () => {
  hideContextMenu()
  clearSelection()
})

// 监听分页数据变化
watch(paginatedItems, () => {
    const visiblePaths = new Set(paginatedItems.value.map(item => item.path))
    const nextSelection = selectedPaths.value.filter(path => visiblePaths.has(path))

    if (nextSelection.length > 0) {
      setSelectedPaths(nextSelection)
    } else if (paginatedItems.value.length > 0) {
      selectSingleItem(paginatedItems.value[0].path)
    } else {
      clearSelection()
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

.drive-nav-button {
  flex: 0 0 auto;
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

.tg-drive-shell.is-inspector-hidden {
  grid-template-columns: 220px minmax(0, 1fr);
}

.tg-filter-rail {
  display: flex;
  flex-direction: column;
  gap: 10px;
  position: sticky;
  top: 0;
}

.tg-rail-section {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tg-rail-section-head {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
  padding: 2px 4px;
}

.tg-rail-section-title {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: #64748b;
}

.tg-rail-section-note {
  font-size: 11px;
  color: #94a3b8;
}

.tg-rail-summary {
  padding: 16px;
  border-radius: 18px;
  border: 1px solid #dbeafe;
  background: linear-gradient(160deg, #f8fbff 0%, #eef6ff 58%, #ffffff 100%);
  box-shadow: 0 18px 30px rgba(59, 130, 246, 0.08);
}

.tg-rail-summary-label {
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  letter-spacing: 0.06em;
  text-transform: uppercase;
}

.tg-rail-summary-size {
  margin-top: 10px;
  font-size: 24px;
  font-weight: 800;
  color: #0f172a;
  line-height: 1.1;
}

.tg-rail-summary-meta {
  margin-top: 8px;
  font-size: 13px;
  color: #64748b;
  line-height: 1.5;
}

.tg-rail-summary-tags {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.tg-rail-summary-tag {
  display: inline-flex;
  align-items: center;
  padding: 4px 10px;
  border-radius: 999px;
  background: rgba(37, 99, 235, 0.08);
  color: #1d4ed8;
  font-size: 12px;
  font-weight: 600;
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

.tg-filter-pill-title {
  display: inline-flex;
  align-items: center;
  gap: 10px;
  min-width: 0;
}

.tg-filter-pill-icon {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 28px;
  height: 28px;
  border-radius: 10px;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  flex: 0 0 auto;
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

.tg-rail-compact {
  display: grid;
  grid-template-columns: 32px minmax(0, 1fr) auto;
  align-items: center;
  gap: 10px;
  width: 100%;
  padding: 12px 14px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: #fff;
  text-align: left;
  transition: all 0.2s ease;
}

.tg-rail-compact:hover,
.tg-rail-compact.is-active {
  border-color: #bfdbfe;
  box-shadow: 0 12px 30px rgba(59, 130, 246, 0.12);
  transform: translateY(-1px);
}

.tg-rail-compact.is-active {
  background: linear-gradient(180deg, #eff6ff 0%, #f8fbff 100%);
}

.tg-rail-compact-mark {
  display: inline-flex;
  align-items: center;
  justify-content: center;
  width: 32px;
  height: 32px;
  border-radius: 12px;
  background: rgba(37, 99, 235, 0.08);
  color: #2563eb;
  font-size: 13px;
  font-weight: 800;
}

.tg-rail-compact-body {
  display: flex;
  flex-direction: column;
  gap: 4px;
  min-width: 0;
}

.tg-rail-compact-title {
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.tg-rail-compact-desc {
  font-size: 11px;
  line-height: 1.4;
  color: #64748b;
}

.tg-rail-compact-count {
  font-size: 12px;
  font-weight: 700;
  color: #2563eb;
}

.tg-drive-main {
  min-width: 0;
  outline: none;
}

.tg-stream-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  padding: 16px 18px;
  border-radius: 18px;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  border: 1px solid #e2e8f0;
  margin-bottom: 14px;
}

.tg-stream-header-main {
  flex: 1;
  min-width: 0;
}

.tg-stream-header-side {
  display: flex;
  align-items: center;
  justify-content: flex-end;
  gap: 8px;
  flex-wrap: wrap;
}

.tg-selection-bar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  flex-wrap: wrap;
  padding: 12px 16px;
  border: 1px solid #dbeafe;
  border-radius: 16px;
  background: linear-gradient(180deg, #f8fbff 0%, #eff6ff 100%);
  margin-bottom: 14px;
}

.tg-selection-summary {
  font-size: 13px;
  font-weight: 700;
  color: #1e3a8a;
}

.tg-selection-detail {
  margin-left: 8px;
  font-weight: 500;
  color: #475569;
}

.tg-selection-actions {
  display: flex;
  align-items: center;
  gap: 8px;
  flex-wrap: wrap;
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

.tg-stream-search {
  margin-top: 14px;
}

.tg-stream-search-input {
  width: min(520px, 100%);
}

.tg-stream-search-input :deep(.el-input__wrapper) {
  min-height: 42px;
  border-radius: 14px;
  background: #f8fafc;
  box-shadow: none;
  border: 1px solid #dbeafe;
}

.tg-stream-active-filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-top: 14px;
}

.tg-stream-filter-chip {
  display: inline-flex;
  align-items: center;
  padding: 8px 12px;
  border: 1px solid #dbeafe;
  border-radius: 999px;
  background: #ffffff;
  color: #2563eb;
  font-size: 12px;
  font-weight: 700;
}

.tg-stream-filter-chip.is-muted {
  color: #475569;
  border-color: #e2e8f0;
}

.tg-stream-filter-chip.is-soft {
  color: #0f766e;
  border-color: #ccfbf1;
  background: #f0fdfa;
}

.tg-group-hero {
  display: grid;
  grid-template-columns: 168px minmax(0, 1fr);
  gap: 18px;
  padding: 18px;
  margin-bottom: 14px;
  border-radius: 20px;
  border: 1px solid #dbeafe;
  background: linear-gradient(135deg, #f8fbff 0%, #eef6ff 48%, #ffffff 100%);
  box-shadow: 0 20px 36px rgba(59, 130, 246, 0.08);
}

.tg-group-hero-collage {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 6px;
  min-height: 168px;
  padding: 6px;
  border-radius: 18px;
  background: rgba(255, 255, 255, 0.7);
}

.tg-group-hero-tile,
.tg-group-hero-image {
  width: 100%;
  height: 100%;
}

.tg-group-hero-tile {
  overflow: hidden;
  border-radius: 12px;
  background: rgba(255, 255, 255, 0.7);
}

.tg-group-hero-fallback,
.tg-group-hero-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  background: rgba(255, 255, 255, 0.76);
}

.tg-group-hero-empty {
  grid-column: 1 / -1;
  grid-row: 1 / -1;
  border-radius: 14px;
}

.tg-group-hero-body {
  min-width: 0;
}

.tg-group-hero-eyebrow {
  font-size: 12px;
  font-weight: 800;
  letter-spacing: 0.08em;
  text-transform: uppercase;
  color: #2563eb;
}

.tg-group-hero-title {
  margin-top: 8px;
  font-size: 24px;
  font-weight: 800;
  line-height: 1.2;
  color: #0f172a;
  word-break: break-word;
}

.tg-group-hero-description {
  margin-top: 10px;
  font-size: 13px;
  line-height: 1.6;
  color: #475569;
}

.tg-group-hero-stats {
  display: grid;
  grid-template-columns: repeat(4, minmax(0, 1fr));
  gap: 10px;
  margin-top: 16px;
}

.tg-group-hero-stat {
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px 14px;
  border-radius: 16px;
  background: rgba(255, 255, 255, 0.78);
  border: 1px solid rgba(219, 234, 254, 0.9);
}

.tg-group-hero-stat span {
  font-size: 11px;
  color: #64748b;
}

.tg-group-hero-stat strong {
  font-size: 14px;
  line-height: 1.45;
  color: #0f172a;
  word-break: break-word;
}

.tg-stream-list {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.tg-list-header {
  display: grid;
  grid-template-columns: minmax(260px, 1.4fr) minmax(220px, 1fr) 110px 160px 164px;
  gap: 14px;
  padding: 0 16px;
  margin-bottom: 4px;
}

.tg-list-header-cell {
  padding: 0;
  border: none;
  background: transparent;
  font-size: 12px;
  font-weight: 700;
  color: #64748b;
  text-align: left;
}

.tg-list-header-cell.is-size,
.tg-list-header-cell.is-time,
.tg-list-header-cell.is-actions {
  text-align: right;
}

.tg-list-header-sort {
  margin-left: 4px;
  color: #2563eb;
}

.tg-file-row {
  display: grid;
  grid-template-columns: minmax(260px, 1.4fr) minmax(220px, 1fr) 110px 160px 164px;
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
  box-shadow: 0 16px 32px rgba(59, 130, 246, 0.14);
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

.tg-file-primary {
  display: flex;
  align-items: flex-start;
  gap: 14px;
  min-width: 0;
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

.tg-group-stack {
  width: 100%;
  height: 100%;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 3px;
  padding: 3px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.tg-group-stack-tile,
.tg-group-stack-image {
  width: 100%;
  height: 100%;
}

.tg-group-stack-tile {
  overflow: hidden;
  border-radius: 8px;
  background: rgba(255, 255, 255, 0.66);
}

.tg-group-stack-fallback,
.tg-group-stack-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  background: rgba(255, 255, 255, 0.7);
}

.tg-group-stack-empty {
  grid-column: 1 / -1;
  grid-row: 1 / -1;
  border-radius: 14px;
}

.tg-file-body {
  min-width: 0;
}

.tg-file-title-row {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
  gap: 10px;
}

.tg-file-title {
  min-width: 0;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  white-space: normal;
  word-break: break-word;
  line-height: 1.35;
  font-size: 15px;
  font-weight: 700;
  color: #0f172a;
}

.tg-file-type-tag {
  flex: 0 0 auto;
  justify-self: end;
  margin-top: 1px;
}

.tg-file-meta {
  margin-top: 6px;
  font-size: 13px;
  color: #475569;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tg-file-path {
  margin-top: 6px;
  font-size: 12px;
  color: #94a3b8;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tg-file-primary-meta {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.tg-file-description,
.tg-file-size,
.tg-file-time,
.tg-file-actions-col {
  display: flex;
  flex-direction: column;
  justify-content: center;
  min-width: 0;
}

.tg-file-description {
  gap: 6px;
}

.tg-file-description-main,
.tg-file-description-sub {
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
}

.tg-file-description-main {
  font-size: 13px;
  color: #334155;
}

.tg-file-description-sub {
  font-size: 12px;
  color: #94a3b8;
}

.tg-file-size {
  align-items: flex-end;
  font-size: 13px;
  font-weight: 700;
  color: #0f172a;
}

.tg-file-time {
  align-items: flex-end;
  gap: 4px;
}

.tg-file-time-main {
  font-size: 12px;
  color: #64748b;
  text-align: right;
}

.tg-file-time-sub {
  font-size: 11px;
  color: #94a3b8;
  text-align: right;
}

.tg-file-actions-col {
  align-items: flex-end;
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

.tg-inspector-group-collage {
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 6px;
  width: 100%;
  height: 100%;
  padding: 8px;
}

.tg-inspector-group-tile,
.tg-inspector-group-image {
  width: 100%;
  height: 100%;
}

.tg-inspector-group-tile {
  overflow: hidden;
  border-radius: 14px;
  background: rgba(255, 255, 255, 0.68);
}

.tg-inspector-group-fallback,
.tg-inspector-group-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  background: rgba(255, 255, 255, 0.76);
  color: #2563eb;
}

.tg-inspector-group-empty {
  grid-column: 1 / -1;
  grid-row: 1 / -1;
  border-radius: 16px;
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
  line-height: 1.35;
  color: #0f172a;
  word-break: break-word;
  overflow: hidden;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 3;
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
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
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

.grid-item.is-active {
  border-color: #60a5fa;
  box-shadow: 0 0 0 2px rgba(96, 165, 250, 0.18), 0 10px 24px rgba(59, 130, 246, 0.14);
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

.grid-group-collage {
  position: relative;
  display: grid;
  grid-template-columns: repeat(2, 1fr);
  grid-template-rows: repeat(2, 1fr);
  gap: 4px;
  width: 100%;
  height: 100%;
  padding: 6px;
  background: linear-gradient(135deg, #eff6ff 0%, #dbeafe 100%);
}

.grid-group-collage-tile,
.grid-group-collage-image {
  width: 100%;
  height: 100%;
}

.grid-group-collage-tile {
  overflow: hidden;
  border-radius: 10px;
  background: rgba(255, 255, 255, 0.65);
}

.grid-group-collage-fallback,
.grid-group-collage-empty {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #2563eb;
  background: rgba(255, 255, 255, 0.74);
}

.grid-group-collage-empty {
  grid-column: 1 / -1;
  grid-row: 1 / -1;
  border-radius: 12px;
}

.grid-group-badge {
  position: absolute;
  left: 8px;
  right: 8px;
  bottom: 8px;
  padding: 4px 8px;
  border-radius: 8px;
  background: rgba(15, 23, 42, 0.74);
  color: #fff;
  font-size: 11px;
  font-weight: 700;
  line-height: 1.35;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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
  font-size: 14px;
  line-height: 1.4;
  text-align: left;
  overflow: hidden;
  word-break: break-word;
  display: -webkit-box;
  -webkit-box-orient: vertical;
  -webkit-line-clamp: 2;
  min-height: calc(1.4em * 2);
}

.grid-item-info {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
  min-height: 24px;
  margin-top: auto;
}

.grid-item-size {
  min-width: 0;
  font-size: 12px;
  color: #909399;
  overflow: hidden;
  text-overflow: ellipsis;
  white-space: nowrap;
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

.tg-context-menu {
  position: fixed;
  z-index: 2100;
  min-width: 176px;
  padding: 8px;
  border-radius: 14px;
  border: 1px solid #dbeafe;
  background: rgba(255, 255, 255, 0.98);
  box-shadow: 0 18px 40px rgba(15, 23, 42, 0.18);
  backdrop-filter: blur(10px);
}

.tg-context-menu-item {
  width: 100%;
  padding: 9px 10px;
  border: none;
  border-radius: 10px;
  background: transparent;
  text-align: left;
  font-size: 13px;
  color: #0f172a;
}

.tg-context-menu-item:hover:not(:disabled) {
  background: #eff6ff;
}

.tg-context-menu-item:disabled {
  color: #94a3b8;
}

.tg-context-menu-item.is-danger {
  color: #dc2626;
}

.tg-context-menu-separator {
  height: 1px;
  margin: 6px 4px;
  background: #e2e8f0;
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

  .tg-group-hero {
    grid-template-columns: 1fr;
  }

  .tg-group-hero-stats {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .tg-stream-header-side {
    justify-content: flex-start;
  }

  .tg-stream-search-input {
    width: 100%;
  }

  .tg-list-header {
    display: none;
  }

  .tg-file-size,
  .tg-file-time,
  .tg-file-actions-col {
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

  .tg-selection-bar {
    align-items: stretch;
  }
}
</style>
