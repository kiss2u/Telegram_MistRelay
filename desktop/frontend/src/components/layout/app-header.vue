<template>
  <el-header class="header">
    <div class="header-content">
      <!-- 左侧:面包屑导航 -->
      <div class="header-left">
        <el-breadcrumb separator="/" class="breadcrumb">
          <el-breadcrumb-item :to="{ path: '/dashboard' }" class="breadcrumb-item">
            <el-icon class="breadcrumb-icon"><HomeFilled /></el-icon>
            <span>首页</span>
          </el-breadcrumb-item>
          <el-breadcrumb-item v-if="breadcrumb && route.path !== '/dashboard'">
            {{ breadcrumb }}
          </el-breadcrumb-item>
        </el-breadcrumb>
      </div>
      
      <!-- 右侧:用户信息 -->
      <div class="header-right">
        <div class="connection-pill" @click="router.push('/settings')">
          <span class="connection-dot" :class="connectionStatusClass"></span>
          <div class="connection-copy">
            <span class="connection-title">{{ connectionTitle }}</span>
            <span class="connection-subtitle">{{ connectionSubtitle }}</span>
          </div>
        </div>

        <el-dropdown trigger="click" @command="handleCommand" placement="bottom-end" class="user-dropdown">
          <div class="user-info">
            <el-avatar :size="40" class="avatar">
              <el-icon><User /></el-icon>
            </el-avatar>
            <div class="user-details">
              <span class="username">{{ authStore.user?.username || '用户' }}</span>
              <span class="user-role">{{ authStore.user?.role === 'admin' ? '系统管理员' : '用户' }}</span>
            </div>
            <el-icon class="dropdown-icon"><ArrowDown /></el-icon>
          </div>
          <template #dropdown>
            <el-dropdown-menu class="user-menu">
              <el-dropdown-item command="password" class="menu-item">
                <el-icon><Lock /></el-icon>
                <span>修改密码</span>
              </el-dropdown-item>
              <el-dropdown-item command="logout" divided class="menu-item logout-item">
                <el-icon><SwitchButton /></el-icon>
                <span>退出登录</span>
              </el-dropdown-item>
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </div>
    </div>

    <!-- 修改密码对话框（append-to-body 脱离 header 的布局约束） -->
    <el-dialog v-model="passwordDialogVisible" title="修改密码" width="420px" :close-on-click-modal="false" append-to-body>
      <el-form ref="pwdFormRef" :model="pwdForm" :rules="pwdRules" label-width="80px">
        <el-form-item label="旧密码" prop="oldPassword">
          <el-input v-model="pwdForm.oldPassword" type="password" show-password placeholder="请输入旧密码" />
        </el-form-item>
        <el-form-item label="新密码" prop="newPassword">
          <el-input v-model="pwdForm.newPassword" type="password" show-password placeholder="至少6位" />
        </el-form-item>
        <el-form-item label="确认密码" prop="confirmPassword">
          <el-input v-model="pwdForm.confirmPassword" type="password" show-password placeholder="再次输入新密码" />
        </el-form-item>
      </el-form>
      <template #footer>
        <el-button @click="passwordDialogVisible = false">取消</el-button>
        <el-button type="primary" :loading="pwdLoading" @click="submitPassword">确认修改</el-button>
      </template>
    </el-dialog>
  </el-header>
</template>

<script setup lang="ts">
import { computed, ref, reactive, onMounted, onUnmounted } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { User, ArrowDown, SwitchButton, HomeFilled, Lock } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import { changePassword } from '@/api'
import { checkServerConnection } from '@/utils/connection'
import { getServerBaseUrl } from '@/utils/runtime'

const route = useRoute()
const router = useRouter()
const authStore = useAuthStore()
const connectionState = ref<'idle' | 'success' | 'error'>('idle')
const connectionMessage = ref('正在检查连接')
let connectionTimer: number | null = null

onMounted(() => {
  if (!authStore.user) {
    authStore.fetchUser()
  }

  void refreshConnectionStatus()
  connectionTimer = window.setInterval(() => {
    void refreshConnectionStatus()
  }, 30000)
})

onUnmounted(() => {
  if (connectionTimer !== null) {
    window.clearInterval(connectionTimer)
  }
})

const breadcrumb = computed(() => {
  const routeMap: Record<string, string> = {
    '/downloads': '下载管理',
    '/settings': '系统设置',
    '/drive': '网盘管理',
    '/local-downloads': '本地下载管理',
  }
  return routeMap[route.path]
})

const connectionTitle = computed(() => {
  const serverBaseUrl = getServerBaseUrl()

  if (!serverBaseUrl) {
    return '未配置服务器'
  }

  try {
    return new URL(serverBaseUrl).host
  } catch {
    return serverBaseUrl
  }
})

const connectionSubtitle = computed(() => {
  if (connectionState.value === 'success') return '服务器在线'
  if (connectionState.value === 'error') return connectionMessage.value
  return '检查连接中'
})

const connectionStatusClass = computed(() => {
  if (connectionState.value === 'success') return 'connection-dot--success'
  if (connectionState.value === 'error') return 'connection-dot--error'
  return 'connection-dot--idle'
})

async function refreshConnectionStatus() {
  const result = await checkServerConnection()
  connectionState.value = result.ok ? 'success' : 'error'
  connectionMessage.value = result.message
}

// 修改密码
const passwordDialogVisible = ref(false)
const pwdLoading = ref(false)
const pwdFormRef = ref<FormInstance>()
const pwdForm = reactive({ oldPassword: '', newPassword: '', confirmPassword: '' })
const pwdRules = {
  oldPassword: [{ required: true, message: '请输入旧密码', trigger: 'blur' }],
  newPassword: [
    { required: true, message: '请输入新密码', trigger: 'blur' },
    { min: 6, message: '密码长度不能少于6位', trigger: 'blur' },
  ],
  confirmPassword: [
    { required: true, message: '请确认新密码', trigger: 'blur' },
    {
      validator: (_: any, value: string, callback: any) => {
        if (value !== pwdForm.newPassword) callback(new Error('两次密码不一致'))
        else callback()
      },
      trigger: 'blur',
    },
  ],
}

async function submitPassword() {
  if (!pwdFormRef.value) return
  const valid = await pwdFormRef.value.validate().catch(() => false)
  if (!valid) return
  pwdLoading.value = true
  try {
    const res = await changePassword(pwdForm.oldPassword, pwdForm.newPassword)
    if (res.success) {
      ElMessage.success('密码修改成功，请重新登录')
      passwordDialogVisible.value = false
      authStore.logout()
      router.push('/login')
    } else {
      ElMessage.error(res.error || '修改失败')
    }
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || '修改失败')
  } finally {
    pwdLoading.value = false
  }
}

function handleCommand(command: string) {
  if (command === 'logout') {
    authStore.logout()
    router.push('/login')
    ElMessage.success('已退出登录')
  } else if (command === 'password') {
    pwdForm.oldPassword = ''
    pwdForm.newPassword = ''
    pwdForm.confirmPassword = ''
    passwordDialogVisible.value = true
  }
}
</script>

<style scoped>
.header {
  @apply bg-white/80;
  backdrop-filter: blur(12px);
  -webkit-backdrop-filter: blur(12px);
  border-bottom: 1px solid rgba(229, 231, 235, 0.5);
  height: 64px !important;
  width: 100% !important;
  position: sticky;
  top: 0;
  z-index: 100;
  box-sizing: border-box;
  margin: 0;
  padding: 0;
  flex-shrink: 0;
  box-shadow: 0 1px 3px 0 rgba(0, 0, 0, 0.05), 0 1px 2px 0 rgba(0, 0, 0, 0.03);
  transition: all 0.3s ease;
}

.header:hover {
  box-shadow: 0 4px 6px -1px rgba(0, 0, 0, 0.08), 0 2px 4px -1px rgba(0, 0, 0, 0.04);
}

.header-content {
  @apply flex items-center justify-between;
  height: 100%;
  padding: 0 24px;
  max-width: 100%;
}

.header-left {
  @apply flex items-center flex-1;
  min-width: 0;
}

.breadcrumb {
  @apply text-sm;
}

:deep(.el-breadcrumb__inner) {
  @apply font-medium text-gray-600;
  display: flex;
  align-items: center;
  gap: 6px;
  transition: all 0.2s ease;
}

:deep(.el-breadcrumb__inner.is-link) {
  @apply text-gray-500;
  transition: color 0.2s;
}

:deep(.el-breadcrumb__inner.is-link:hover) {
  color: #667eea;
  transform: translateX(2px);
}

:deep(.el-breadcrumb__separator) {
  @apply text-gray-400 mx-2;
}

.breadcrumb-icon {
  @apply text-gray-500;
  font-size: 16px;
  transition: all 0.2s ease;
}

:deep(.el-breadcrumb__inner.is-link:hover) .breadcrumb-icon {
  color: #667eea;
  transform: scale(1.1);
}

.header-right {
  @apply flex items-center gap-3;
  flex-shrink: 0;
}

.connection-pill {
  @apply flex items-center gap-3;
  min-width: 220px;
  padding: 8px 14px;
  border-radius: 12px;
  border: 1px solid rgba(229, 231, 235, 0.9);
  background: rgba(255, 255, 255, 0.82);
  cursor: pointer;
  transition: all 0.2s ease;
}

.connection-pill:hover {
  border-color: rgba(102, 126, 234, 0.25);
  box-shadow: 0 8px 20px rgba(102, 126, 234, 0.08);
  transform: translateY(-1px);
}

.connection-dot {
  width: 10px;
  height: 10px;
  border-radius: 999px;
  flex-shrink: 0;
  box-shadow: 0 0 0 6px rgba(148, 163, 184, 0.12);
}

.connection-dot--success {
  background: #10b981;
  box-shadow: 0 0 0 6px rgba(16, 185, 129, 0.12);
}

.connection-dot--error {
  background: #ef4444;
  box-shadow: 0 0 0 6px rgba(239, 68, 68, 0.12);
}

.connection-dot--idle {
  background: #f59e0b;
  box-shadow: 0 0 0 6px rgba(245, 158, 11, 0.12);
}

.connection-copy {
  @apply flex flex-col;
  min-width: 0;
}

.connection-title {
  @apply text-sm font-semibold text-gray-800;
  line-height: 1.2;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.connection-subtitle {
  @apply text-xs text-gray-500;
  line-height: 1.2;
  margin-top: 3px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.user-dropdown {
  @apply cursor-pointer;
}

.user-info {
  @apply flex items-center gap-3 cursor-pointer;
  padding: 8px 16px;
  border-radius: 12px;
  transition: all 0.3s ease;
  border: 1px solid transparent;
  background: linear-gradient(135deg, rgba(255, 255, 255, 0.9), rgba(249, 250, 251, 0.9));
}

.user-info:hover {
  background: linear-gradient(135deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.05));
  border-color: rgba(102, 126, 234, 0.2);
  box-shadow: 0 4px 12px rgba(102, 126, 234, 0.15);
  transform: translateY(-1px);
}

.avatar {
  background: var(--gradient-primary);
  @apply text-white;
  flex-shrink: 0;
  box-shadow: 0 4px 8px rgba(102, 126, 234, 0.3);
  transition: all 0.3s ease;
}

.user-info:hover .avatar {
  box-shadow: 0 6px 12px rgba(102, 126, 234, 0.4);
  transform: scale(1.05);
}

.user-details {
  @apply flex flex-col items-start;
  min-width: 0;
}

.username {
  @apply text-gray-900 font-semibold text-sm;
  line-height: 1.3;
  white-space: nowrap;
}

.user-role {
  @apply text-gray-500 text-xs;
  line-height: 1.3;
  margin-top: 2px;
}

.dropdown-icon {
  @apply text-gray-400;
  font-size: 14px;
  transition: all 0.3s ease;
  flex-shrink: 0;
  margin-left: 4px;
}

.user-info:hover .dropdown-icon {
  color: #667eea;
  transform: translateY(2px);
}

.user-menu {
  @apply mt-2;
  min-width: 180px;
  border-radius: 12px;
  box-shadow: 0 12px 24px rgba(0, 0, 0, 0.12);
  border: 1px solid rgba(229, 231, 235, 0.8);
  overflow: hidden;
}

.menu-item {
  @apply flex items-center gap-3;
  padding: 12px 20px;
  transition: all 0.2s ease;
}

.menu-item:hover {
  background: linear-gradient(90deg, rgba(102, 126, 234, 0.08), rgba(118, 75, 162, 0.05));
}

.menu-item :deep(.el-icon) {
  font-size: 18px;
  color: #667eea;
  transition: transform 0.2s ease;
}

.menu-item:hover :deep(.el-icon) {
  transform: scale(1.1);
}

.menu-item :deep(span) {
  @apply text-sm font-medium;
}

.logout-item {
  border-top: 1px solid rgba(229, 231, 235, 0.8);
}

.logout-item :deep(.el-icon) {
  color: #ef4444;
}

.logout-item:hover {
  background: linear-gradient(90deg, rgba(239, 68, 68, 0.08), rgba(220, 38, 38, 0.05));
}
</style>
