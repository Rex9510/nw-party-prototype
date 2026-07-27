/**
 * 认证状态管理（Pinia）- Web 版本用 localStorage
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
  street_name: string | null
  community_name: string | null
  branch_name: string | null
}

interface AuthState {
  token: string
  refreshToken: string
  user: UserInfo | null
}

const STORAGE_KEY = 'nwparty_auth'

function loadFromStorage(): Partial<AuthState> {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
    return raw ? JSON.parse(raw) : {}
  } catch {
    return {}
  }
}

function saveToStorage(state: Partial<AuthState>) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(state))
}

function clearStorage() {
  localStorage.removeItem(STORAGE_KEY)
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
      // 关键：先把 token 写进 localStorage，下一次 fetchMe 才能拿到
      this._persist()
      try {
        await this.fetchMe()
      } catch (e) {
        // fetchMe 失败时清掉 storage，让用户重新登录
        this.logout()
        throw e
      }
    },

    async fetchMe() {
      this.user = await api.get<UserInfo>('/auth/me')
      this._persist()
    },

    logout() {
      this.token = ''
      this.refreshToken = ''
      this.user = null
      clearStorage()
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
