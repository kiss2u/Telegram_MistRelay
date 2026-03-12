import { defineStore } from 'pinia'
import { api } from '@/api'
import { clearAuthToken, getAuthToken, setAuthToken } from '@/utils/runtime'

interface UserInfo {
  id: number
  username: string
  role: string
}

interface AuthState {
  token: string | null
  user: UserInfo | null
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => ({
    token: getAuthToken(),
    user: null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await api.post('/auth/login', { username, password })
      if (!data.success) throw new Error(data.error || '登录失败')
      this.token = data.token
      this.user = data.user
      setAuthToken(data.token)
    },

    async fetchUser() {
      if (!this.token) return
      try {
        const { data } = await api.get('/auth/me', {
          headers: { Authorization: `Bearer ${this.token}` },
        })
        if (data.success) {
          this.user = data.user
        } else {
          this.logout()
        }
      } catch {
        this.logout()
      }
    },

    logout() {
      this.token = null
      this.user = null
      clearAuthToken()
    },
  },
})
