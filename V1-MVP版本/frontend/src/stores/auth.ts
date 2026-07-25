/**
 * 认证状态管理（Pinia）。
 * - token 持久化到 localStorage
 * - 提供 login/logout/refreshMe
 */
import { defineStore } from 'pinia'
import { api } from '@/utils/request'

export interface UserInfo {
  id: number
  phone: string
  name: string
  role: string
  street_id: number | null
  community_id: number | null
  branch_id: number | null
}

interface AuthState {
  token: string
  refreshToken: string
  user: UserInfo | null
}

const STORAGE_KEY = 'nwparty_auth'

function loadFromStorage(): Partial<AuthState> {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveToStorage(state: Partial<AuthState>) {
  uni.setStorageSync(STORAGE_KEY, JSON.stringify(state))
}

export const useAuthStore = defineStore('auth', {
  state: (): AuthState => {
    const cached = loadFromStorage()
    return {
      token: cached.token || '',
      refreshToken: cached.refreshToken || '',
      user: cached.user || null,
    }
  },

  actions: {
    async login(phone: string, password: string) {
      const res = await api.post<{
        access_token: string
        refresh_token: string
        expires_in: number
      }>('/auth/login', { phone, password })
      this.token = res.access_token
      this.refreshToken = res.refresh_token
      await this.fetchMe()
      this._persist()
    },

    async fetchMe() {
      this.user = await api.get<UserInfo>('/auth/me')
      this._persist()
    },

    logout() {
      this.token = ''
      this.refreshToken = ''
      this.user = null
      uni.removeStorageSync(STORAGE_KEY)
    },

    _persist() {
      saveToStorage({
        token: this.token,
        refreshToken: this.refreshToken,
        user: this.user,
      })
    },
  },
})
