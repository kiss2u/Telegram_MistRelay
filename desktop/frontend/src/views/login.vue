<template>
  <div class="login-page">
    <div class="login-bg">
      <div class="bg-circle bg-circle-1"></div>
      <div class="bg-circle bg-circle-2"></div>
      <div class="bg-circle bg-circle-3"></div>
    </div>

    <div class="login-card glass-card animate-scale-in">
      <div class="login-header">
        <div class="logo-icon">
          <el-icon :size="36"><Monitor /></el-icon>
        </div>
        <h1 class="text-gradient">MistRelay</h1>
        <p class="login-subtitle">媒体中继管理系统</p>
      </div>

      <el-form
        ref="formRef"
        :model="form"
        :rules="rules"
        class="login-form"
        @submit.prevent="handleLogin"
      >
        <el-form-item prop="username">
          <el-input
            v-model="form.username"
            placeholder="用户名"
            size="large"
            :prefix-icon="User"
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item prop="password">
          <el-input
            v-model="form.password"
            type="password"
            placeholder="密码"
            size="large"
            :prefix-icon="Lock"
            show-password
            @keyup.enter="handleLogin"
          />
        </el-form-item>
        <el-form-item prop="serverUrl">
          <el-input
            v-model="form.serverUrl"
            placeholder="服务器地址，示例: https://mistrelay.example.com"
            size="large"
            :prefix-icon="Link"
          />
        </el-form-item>
        <el-form-item>
          <el-button
            type="primary"
            size="large"
            class="login-btn"
            :loading="loading"
            @click="handleLogin"
          >
            {{ loading ? '登录中...' : '登 录' }}
          </el-button>
        </el-form-item>
      </el-form>

      <p class="server-hint">
        {{ serverHint }}
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import { User, Lock, Monitor, Link } from '@element-plus/icons-vue'
import { useAuthStore } from '@/stores/auth'
import {
  getDefaultServerBaseUrl,
  getServerBaseUrl,
  isValidServerBaseUrl,
  normalizeServerBaseUrl,
  setServerBaseUrl,
} from '@/utils/runtime'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  serverUrl: getServerBaseUrl() || getDefaultServerBaseUrl(),
})

const rules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }],
  serverUrl: [{
    validator: (_rule: unknown, value: string, callback: (error?: Error) => void) => {
      if (!value) {
        callback(new Error('桌面端需要填写服务器地址'))
        return
      }

      const normalized = normalizeServerBaseUrl(value)
      if (!/^https?:\/\//i.test(normalized) && !normalized.startsWith('/')) {
        callback(new Error('服务器地址必须是 http(s) 地址'))
        return
      }

      if (!isValidServerBaseUrl(normalized)) {
        callback(new Error('服务器地址格式不正确'))
        return
      }

      callback()
    },
    trigger: 'blur'
  }],
}

const serverHint = '桌面端会直接连接远程 MistRelay 服务，所有下载与上传逻辑都运行在服务器。'

async function handleLogin() {
  if (!formRef.value) return
  const valid = await formRef.value.validate().catch(() => false)
  if (!valid) return

  loading.value = true
  try {
    setServerBaseUrl(form.serverUrl)
    await authStore.login(form.username, form.password)
    ElMessage.success('登录成功')
    router.replace('/')
  } catch (e: any) {
    ElMessage.error(e.response?.data?.error || e.message || '登录失败')
  } finally {
    loading.value = false
  }
}
</script>

<style scoped>
.login-page {
  min-height: 100vh;
  display: flex;
  align-items: center;
  justify-content: center;
  position: relative;
  overflow: hidden;
  background: linear-gradient(135deg, #667eea 0%, #764ba2 100%);
}

.login-bg {
  position: absolute;
  inset: 0;
  overflow: hidden;
}

.bg-circle {
  position: absolute;
  border-radius: 50%;
  opacity: 0.15;
  filter: blur(60px);
}

.bg-circle-1 {
  width: 500px;
  height: 500px;
  background: #fff;
  top: -10%;
  left: -5%;
  animation: float 8s ease-in-out infinite;
}

.bg-circle-2 {
  width: 400px;
  height: 400px;
  background: #a78bfa;
  bottom: -8%;
  right: -3%;
  animation: float 10s ease-in-out infinite reverse;
}

.bg-circle-3 {
  width: 300px;
  height: 300px;
  background: #f0abfc;
  top: 40%;
  right: 20%;
  animation: float 12s ease-in-out infinite;
}

.login-card {
  width: 400px;
  max-width: 90vw;
  padding: 40px 36px 28px;
  border-radius: 20px;
  position: relative;
  z-index: 1;
  background: rgba(255, 255, 255, 0.85) !important;
  backdrop-filter: blur(20px) !important;
}

.login-header {
  text-align: center;
  margin-bottom: 32px;
}

.logo-icon {
  width: 64px;
  height: 64px;
  border-radius: 16px;
  background: var(--gradient-primary);
  display: flex;
  align-items: center;
  justify-content: center;
  margin: 0 auto 16px;
  color: #fff;
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.35);
}

.login-header h1 {
  font-size: 28px;
  font-weight: 700;
  margin: 0 0 6px;
}

.login-subtitle {
  color: #9ca3af;
  font-size: 14px;
  margin: 0;
}

.login-form :deep(.el-input__wrapper) {
  border-radius: 10px;
  box-shadow: 0 0 0 1px #e5e7eb inset;
  padding: 4px 12px;
}

.login-form :deep(.el-input__wrapper:hover) {
  box-shadow: 0 0 0 1px var(--color-primary) inset;
}

.server-hint {
  margin: 4px 4px 0;
  color: #6b7280;
  font-size: 12px;
  line-height: 1.6;
}

.login-btn {
  width: 100%;
  border-radius: 10px;
  height: 44px;
  font-size: 16px;
  font-weight: 600;
  background: var(--gradient-primary);
  border: none;
  transition: all 0.3s;
}

.login-btn:hover {
  transform: translateY(-1px);
  box-shadow: 0 8px 24px rgba(102, 126, 234, 0.4);
}
</style>
