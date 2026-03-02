import { defineStore } from 'pinia'
import axios from 'axios'

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
    token: localStorage.getItem('token'),
    user: null,
  }),
  getters: {
    isLoggedIn: (state) => !!state.token,
  },
  actions: {
    async login(username: string, password: string) {
      const { data } = await axios.post('/api/auth/login', { username, password })
      if (!data.success) throw new Error(data.error || '登录失败')
      this.token = data.token
      this.user = data.user
      localStorage.setItem('token', data.token)
    },

    async fetchUser() {
      if (!this.token) return
      try {
        const { data } = await axios.get('/api/auth/me', {
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
      localStorage.removeItem('token')
    },
  },
})
