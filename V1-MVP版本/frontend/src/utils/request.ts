/**
 * API 请求封装（基于 uni.request）。
 * - 自动加 Authorization 头
 * - 401 自动跳登录
 * - 统一错误处理
 */
import { useAuthStore } from '@/stores/auth'

const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'

export interface ApiResponse<T = any> {
  data: T
  statusCode: number
}

class ApiError extends Error {
  statusCode: number
  constructor(message: string, statusCode: number) {
    super(message)
    this.statusCode = statusCode
  }
}

export async function request<T = any>(
  url: string,
  options: UniApp.RequestOptions = {},
): Promise<T> {
  const auth = useAuthStore()
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...(auth.token ? { Authorization: `Bearer ${auth.token}` } : {}),
        ...(options.header || {}),
      },
      success: (res) => {
        if (res.statusCode === 401) {
          auth.logout()
          uni.reLaunch({ url: '/pages/login/index' })
          reject(new ApiError('未登录', 401))
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else {
          const msg = (res.data && (res.data as any).detail) || `请求失败 (${res.statusCode})`
          reject(new ApiError(msg, res.statusCode))
        }
      },
      fail: (err) => reject(new ApiError(err.errMsg || '网络错误', 0)),
    })
  })
}

export const api = {
  get: <T = any>(url: string, data?: any) => request<T>(url, { method: 'GET', data }),
  post: <T = any>(url: string, data?: any) => request<T>(url, { method: 'POST', data }),
  put: <T = any>(url: string, data?: any) => request<T>(url, { method: 'PUT', data }),
  patch: <T = any>(url: string, data?: any) => request<T>(url, { method: 'PATCH', data }),
  delete: <T = any>(url: string) => request<T>(url, { method: 'DELETE' }),
}
