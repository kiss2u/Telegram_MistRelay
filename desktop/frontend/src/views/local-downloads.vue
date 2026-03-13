<template>
  <div class="local-downloads-page">
    <el-card shadow="hover" class="local-downloads-shell">
      <template #header>
        <div class="page-header">
          <div>
            <h2>本地下载管理</h2>
            <p class="page-subtitle">配置和任务分开显示。这里管理桌面端本地下载目录、并发和线程，并单独查看下载任务。</p>
          </div>
          <div class="page-actions">
            <el-button @click="router.push('/drive')">前往网盘下载</el-button>
          </div>
        </div>
      </template>
      <el-tabs v-model="activeTab" class="local-tabs">
        <el-tab-pane name="config">
          <template #label>
            <span class="tab-label">下载配置</span>
          </template>

          <div class="config-panel">
            <el-alert
              title="以下配置只影响当前桌面客户端，不会修改服务器端下载参数。保存后新建的本地下载任务立即按新配置执行。"
              type="info"
              :closable="false"
              style="margin-bottom: 20px"
            />

            <div class="config-summary-grid">
              <div class="summary-tile">
                <div class="summary-label">当前生效目录</div>
                <div class="summary-value is-path" :title="effectiveDesktopDownloadDir">{{ effectiveDesktopDownloadDir }}</div>
              </div>
              <div class="summary-tile">
                <div class="summary-label">默认目录</div>
                <div class="summary-value is-path" :title="defaultDesktopDownloadDir || '读取中...'">{{ defaultDesktopDownloadDir || '读取中...' }}</div>
              </div>
              <div class="summary-tile">
                <div class="summary-label">下载并发</div>
                <div class="summary-value">{{ desktopMaxConcurrent }}</div>
              </div>
              <div class="summary-tile">
                <div class="summary-label">单文件线程</div>
                <div class="summary-value">{{ desktopThreadsPerDownload }}</div>
              </div>
            </div>

            <div class="config-toolbar">
              <el-button @click="loadDownloadConfig" :loading="loadingConfig">重新读取</el-button>
              <el-button type="primary" @click="saveDownloadConfig" :loading="savingConfig">保存配置</el-button>
            </div>

            <el-form label-width="180px" class="config-form">
              <el-form-item label="下载目录">
                <div class="download-dir-row">
                  <el-input
                    v-model="desktopDownloadDir"
                    placeholder="留空则使用系统下载目录下的 MistRelay 文件夹"
                    clearable
                  />
                  <el-button @click="handlePickDownloadDir">选择文件夹</el-button>
                </div>
                <div class="el-form-item__help">
                  请输入绝对路径。留空则自动恢复默认目录。
                </div>
              </el-form-item>

              <el-form-item label="最大并行下载数">
                <el-input-number
                  v-model="desktopMaxConcurrent"
                  :min="1"
                  :max="10"
                  :step="1"
                />
                <div class="el-form-item__help">
                  同时下载多少个文件，超过的任务会排队等待。
                </div>
              </el-form-item>

              <el-form-item label="每文件下载线程数">
                <el-input-number
                  v-model="desktopThreadsPerDownload"
                  :min="1"
                  :max="32"
                  :step="1"
                />
                <div class="el-form-item__help">
                  单个文件用多少个线程并行分片下载。服务器不支持 Range 时会自动回退。
                </div>
              </el-form-item>

              <el-form-item>
                <el-button @click="desktopDownloadDir = ''">恢复默认目录</el-button>
              </el-form-item>
            </el-form>
          </div>
        </el-tab-pane>

        <el-tab-pane name="tasks">
          <template #label>
            <span class="tab-label">
              下载任务
              <el-tag size="small" type="info" effect="plain">{{ desktopDownloadStats.total }}</el-tag>
            </span>
          </template>

          <div class="section-header">
            <div>
              <div class="section-title">下载任务</div>
              <p class="section-subtitle">已开始的任务会保留在当前列表中，方便查看保存位置和失败原因。</p>
            </div>
          </div>

          <div class="stats-grid">
            <div class="stat-card">
              <div class="stat-label">总任务</div>
              <div class="stat-value">{{ desktopDownloadStats.total }}</div>
            </div>
            <div class="stat-card is-active">
              <div class="stat-label">进行中</div>
              <div class="stat-value">{{ desktopDownloadStats.active }}</div>
            </div>
            <div class="stat-card is-success">
              <div class="stat-label">已完成</div>
              <div class="stat-value">{{ desktopDownloadStats.completed }}</div>
            </div>
            <div class="stat-card is-danger">
              <div class="stat-label">失败</div>
              <div class="stat-value">{{ desktopDownloadStats.failed }}</div>
            </div>
          </div>

          <el-empty
            v-if="desktopDownloadList.length === 0"
            description="还没有本地下载任务，请到“我的网盘”里选择文件下载。"
            :image-size="88"
          />

          <div v-else class="downloads-list">
            <div
              v-for="task in desktopDownloadList"
              :key="task.transferId"
              class="download-card"
            >
              <div class="download-card-head">
                <div class="download-main">
                  <div class="download-name" :title="task.fileName">{{ task.fileName }}</div>
                  <div class="download-meta-line">{{ formatDesktopDownloadMeta(task) }}</div>
                </div>
                <el-tag :type="getDesktopDownloadTagType(task)" effect="plain">
                  {{ getDesktopDownloadLabel(task) }}
                </el-tag>
              </div>

              <el-progress
                :percentage="task.progressPercent"
                :status="getDesktopDownloadProgressStatus(task)"
                :indeterminate="!task.totalBytes && task.state !== 'completed' && task.state !== 'error'"
                :duration="2"
                :stroke-width="10"
              />

              <div class="download-detail-row">
                <span class="detail-label">保存位置</span>
                <span class="detail-value" :title="task.localPath">{{ task.localPath }}</span>
              </div>

              <div v-if="task.error" class="download-detail-row is-error">
                <span class="detail-label">错误信息</span>
                <span class="detail-value">{{ task.error }}</span>
              </div>
            </div>
          </div>
        </el-tab-pane>
      </el-tabs>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage } from 'element-plus'
import { useRouter } from 'vue-router'
import { DEFAULT_DOWNLOAD_CONFIG, getDefaultDesktopDownloadDir, getDesktopClientConfig, pickDesktopDownloadDir, saveDesktopClientConfig } from '@/utils/desktop'
import { useDesktopDownloads } from '@/composables/useDesktopDownloads'

const router = useRouter()
const activeTab = ref<'config' | 'tasks'>('config')
const loadingConfig = ref(false)
const savingConfig = ref(false)
const defaultDesktopDownloadDir = ref('')
const desktopDownloadDir = ref(DEFAULT_DOWNLOAD_CONFIG.downloadDir)
const desktopMaxConcurrent = ref(DEFAULT_DOWNLOAD_CONFIG.maxConcurrentDownloads)
const desktopThreadsPerDownload = ref(DEFAULT_DOWNLOAD_CONFIG.threadsPerDownload)
const {
  desktopDownloadList,
  desktopDownloadStats,
  getDesktopDownloadLabel,
  getDesktopDownloadTagType,
  getDesktopDownloadProgressStatus,
  formatDesktopDownloadMeta,
} = useDesktopDownloads()

const effectiveDesktopDownloadDir = computed(() => {
  const configured = desktopDownloadDir.value.trim()
  return configured || defaultDesktopDownloadDir.value || '读取中...'
})

async function loadDownloadConfig(showMessage = false) {
  loadingConfig.value = true
  try {
    const [config, defaultDir] = await Promise.all([
      getDesktopClientConfig(),
      getDefaultDesktopDownloadDir(),
    ])
    const downloadConfig = config.download ?? DEFAULT_DOWNLOAD_CONFIG
    defaultDesktopDownloadDir.value = defaultDir
    desktopDownloadDir.value = downloadConfig.downloadDir ?? ''
    desktopMaxConcurrent.value = downloadConfig.maxConcurrentDownloads
    desktopThreadsPerDownload.value = downloadConfig.threadsPerDownload
    if (showMessage) {
      ElMessage.success('本地下载配置已读取')
    }
  } catch (err: any) {
    console.error('加载本地下载配置失败:', err)
    ElMessage.error(err.message || '加载本地下载配置失败')
  } finally {
    loadingConfig.value = false
  }
}

async function saveDownloadConfig() {
  savingConfig.value = true
  try {
    const current = await getDesktopClientConfig()
    await saveDesktopClientConfig({
      ...current,
      download: {
        downloadDir: desktopDownloadDir.value.trim(),
        maxConcurrentDownloads: desktopMaxConcurrent.value,
        threadsPerDownload: desktopThreadsPerDownload.value,
      },
    })
    ElMessage.success('本地下载配置已保存并立即生效')
    await loadDownloadConfig(false)
  } catch (err: any) {
    console.error('保存本地下载配置失败:', err)
    ElMessage.error(err.message || '保存本地下载配置失败')
  } finally {
    savingConfig.value = false
  }
}

async function handlePickDownloadDir() {
  try {
    const selected = await pickDesktopDownloadDir(desktopDownloadDir.value || defaultDesktopDownloadDir.value)
    if (selected) {
      desktopDownloadDir.value = selected
    }
  } catch (err: any) {
    console.error('选择下载目录失败:', err)
    ElMessage.error(err.message || '选择下载目录失败')
  }
}

onMounted(() => {
  void loadDownloadConfig()
})
</script>

<style scoped>
.local-downloads-page {
  padding: 20px;
}

.local-downloads-shell :deep(.el-card__body) {
  padding-top: 14px;
}

.local-tabs :deep(.el-tabs__header) {
  margin-bottom: 20px;
}

.local-tabs :deep(.el-tabs__nav-wrap::after) {
  height: 1px;
  background: #e2e8f0;
}

.local-tabs :deep(.el-tabs__item) {
  height: 42px;
  font-weight: 600;
  color: #64748b;
}

.local-tabs :deep(.el-tabs__item.is-active) {
  color: #2563eb;
}

.tab-label {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.page-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
  flex-wrap: wrap;
}

.page-header h2 {
  margin: 0;
  font-size: 20px;
  font-weight: 700;
  color: #0f172a;
}

.page-subtitle {
  margin: 8px 0 0;
  max-width: 780px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.page-actions {
  display: flex;
  flex-wrap: wrap;
  gap: 10px;
}

.config-panel {
  display: grid;
  gap: 20px;
}

.config-summary-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 14px;
}

.summary-tile {
  padding: 16px 18px;
  border-radius: 16px;
  border: 1px solid #dbeafe;
  background: linear-gradient(135deg, #f8fbff 0%, #ffffff 100%);
}

.summary-label {
  font-size: 12px;
  color: #64748b;
}

.summary-value {
  margin-top: 8px;
  font-size: 26px;
  font-weight: 700;
  color: #0f172a;
}

.summary-value.is-path {
  font-size: 13px;
  line-height: 1.6;
  font-weight: 600;
  word-break: break-all;
}

.config-toolbar {
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  flex-wrap: wrap;
}

.config-form {
  max-width: 860px;
}

.download-dir-row {
  display: flex;
  gap: 10px;
  width: 100%;
}

.download-dir-row :deep(.el-input) {
  flex: 1;
}

.section-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 16px;
}

.section-title {
  font-size: 18px;
  font-weight: 700;
  color: #0f172a;
}

.section-subtitle {
  margin: 8px 0 20px;
  font-size: 13px;
  line-height: 1.6;
  color: #64748b;
}

.stats-grid {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(160px, 1fr));
  gap: 14px;
  margin-bottom: 20px;
}

.stat-card {
  padding: 16px 18px;
  border-radius: 14px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(135deg, #f8fafc 0%, #ffffff 100%);
}

.stat-card.is-active {
  border-color: #cbd5e1;
  background: linear-gradient(135deg, #eff6ff 0%, #ffffff 100%);
}

.stat-card.is-success {
  border-color: #bbf7d0;
  background: linear-gradient(135deg, #f0fdf4 0%, #ffffff 100%);
}

.stat-card.is-danger {
  border-color: #fecaca;
  background: linear-gradient(135deg, #fef2f2 0%, #ffffff 100%);
}

.stat-label {
  font-size: 12px;
  color: #64748b;
}

.stat-value {
  margin-top: 8px;
  font-size: 28px;
  font-weight: 700;
  color: #0f172a;
}

.downloads-list {
  display: grid;
  gap: 14px;
}

.download-card {
  padding: 18px;
  border-radius: 16px;
  border: 1px solid #e2e8f0;
  background: linear-gradient(180deg, #ffffff 0%, #f8fafc 100%);
  box-shadow: 0 10px 30px rgba(15, 23, 42, 0.04);
}

.download-card-head {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 14px;
}

.download-main {
  min-width: 0;
  flex: 1;
}

.download-name {
  font-size: 15px;
  font-weight: 600;
  color: #0f172a;
  word-break: break-all;
}

.download-meta-line {
  margin-top: 6px;
  font-size: 12px;
  color: #64748b;
}

.download-detail-row {
  display: grid;
  grid-template-columns: 76px 1fr;
  gap: 12px;
  margin-top: 12px;
  font-size: 13px;
}

.download-detail-row.is-error .detail-value {
  color: #dc2626;
}

.detail-label {
  color: #64748b;
}

.detail-value {
  color: #0f172a;
  word-break: break-all;
}
</style>
