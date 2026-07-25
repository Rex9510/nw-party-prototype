/**
 * API 请求封装（基于 uni.request）。
 * - 自动从 storage 读 token 加 Authorization 头
 * - 401 自动清 storage + 跳登录
 * - 统一错误处理
 */

const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'
const STORAGE_KEY = 'nwparty_auth'

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

function getToken(): string {
  try {
    const raw = uni.getStorageSync(STORAGE_KEY)
    if (raw) {
      const parsed = typeof raw === 'string' ? JSON.parse(raw) : raw
      return parsed?.token || ''
    }
  } catch {
    // ignore
  }
  return ''
}

function clearAuthAndRedirect() {
  try {
    uni.removeStorageSync(STORAGE_KEY)
  } catch {
    // ignore
  }
  // 避免在登录页重复跳转
  const pages = getCurrentPages()
  const current = pages.length > 0 ? pages[pages.length - 1] : null
  if (current && current.route !== 'pages/login/index') {
    uni.reLaunch({ url: '/pages/login/index' })
  }
}

export async function request<T = any>(
  url: string,
  options: UniApp.RequestOptions = {},
): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`
  const token = getToken()

  return new Promise((resolve, reject) => {
    uni.request({
      url: fullUrl,
      method: options.method || 'GET',
      data: options.data,
      header: {
        'Content-Type': 'application/json',
        ...(token ? { Authorization: `Bearer ${token}` } : {}),
        ...(options.header || {}),
      },
      success: (res) => {
        if (res.statusCode === 401) {
          clearAuthAndRedirect()
          reject(new ApiError('未登录或登录已过期', 401))
          return
        }
        if (res.statusCode >= 200 && res.statusCode < 300) {
          resolve(res.data as T)
        } else {
          const body = res.data as any
          const detail = body?.detail
          const msg =
            (typeof detail === 'string' ? detail : detail?.msg) ||
            body?.message ||
            `请求失败 (${res.statusCode})`
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
