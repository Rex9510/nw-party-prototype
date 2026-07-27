/**
 * API 请求封装（基于 fetch + Vite proxy）
 * - 自动从 localStorage 读 token 加 Authorization 头
 * - 401 自动清 storage + 跳登录
 * - 统一错误处理
 */

const BASE_URL = import.meta.env.VITE_API_BASE || '/api/v1'
const STORAGE_KEY = 'nwparty_auth'

export class ApiError extends Error {
  statusCode: number
  constructor(message: string, statusCode: number) {
    super(message)
    this.statusCode = statusCode
  }
}

// 不需要 Authorization 头的路径（避免把无意义 token 发过去、避免登录失败时清掉刚拿到的 token）
const SKIP_AUTH_PATHS = ['/auth/login', '/auth/refresh', '/public/']

function getToken(): string {
  try {
    const raw = localStorage.getItem(STORAGE_KEY)
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
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // ignore
  }
  if (window.location.pathname !== '/pages/login/index') {
    window.location.href = '/pages/login/index'
  }
}

export async function request<T = any>(
  url: string,
  options: { method?: string; data?: any; header?: Record<string, string> } = {},
): Promise<T> {
  const fullUrl = url.startsWith('http') ? url : `${BASE_URL}${url}`
  const token = getToken()
  const method = (options.method || 'GET').toUpperCase()

  // 登录/刷新/公开接口不需要带旧 token
  const skipAuth = SKIP_AUTH_PATHS.some((p) => p.endsWith('/') ? url.includes(p) : url.endsWith(p))
  const headers: Record<string, string> = {
    'Content-Type': 'application/json',
    ...(token && !skipAuth ? { Authorization: `Bearer ${token}` } : {}),
    ...(options.header || {}),
  }

  let body: string | undefined
  if (options.data !== undefined && method !== 'GET' && method !== 'HEAD') {
    body = JSON.stringify(options.data)
  }

  const queryString =
    method === 'GET' && options.data
      ? '?' + new URLSearchParams(
          Object.entries(options.data)
            .filter(([, v]) => v !== undefined && v !== null && v !== '')
            .map(([k, v]) => [k, String(v)]),
        ).toString()
      : ''

  const res = await fetch(fullUrl + queryString, {
    method,
    headers,
    body,
  })
  // 调试日志
  console.log('[request]', method, fullUrl + queryString, '->', res.status)

  if (res.status === 401) {
    // 登录/刷新接口的 401 是凭据错/刷新失败，不要清掉 storage 跳登录页
    // 让上层 catch 显示具体错误
    if (!skipAuth) {
      clearAuthAndRedirect()
    }
    // 默认中文；后端 detail 是英文（如 FastAPI 自带的 "Not authenticated"）时翻译成中文
    let msg = '未登录或登录已过期'
    try {
      const data = await res.clone().json()
      if (typeof data?.detail === 'string') {
        msg = translateDetail(data.detail) || msg
      }
    } catch {
      // ignore
    }
    throw new ApiError(msg, 401)
  }

  if (!res.ok) {
    let msg = `请求失败 (${res.status})`
    try {
      const data = await res.json()
      const detail = data?.detail
      if (typeof detail === 'string') {
        msg = detail
      } else if (detail?.msg) {
        msg = detail.msg
      } else if (data?.message) {
        msg = data.message
      }
    } catch {
      // ignore
    }
    throw new ApiError(msg, res.status)
  }

  if (res.status === 204) {
    return undefined as T
  }

  return (await res.json()) as T
}

export const api = {
  get: <T = any>(url: string, data?: any) => request<T>(url, { method: 'GET', data }),
  post: <T = any>(url: string, data?: any) => request<T>(url, { method: 'POST', data }),
  put: <T = any>(url: string, data?: any) => request<T>(url, { method: 'PUT', data }),
  patch: <T = any>(url: string, data?: any) => request<T>(url, { method: 'PATCH', data }),
  delete: <T = any>(url: string) => request<T>(url, { method: 'DELETE' }),
}

/**
 * 把后端可能返回的英文 detail 翻译成中文（401 专用）。
 * 后端没启翻译时前端兜底。
 * 返回空字符串表示不需要翻译。
 */
function translateDetail(detail: string): string {
  const d = detail.trim().toLowerCase()
  if (!d) return ''
  if (d === 'not authenticated' || d === 'unauthenticated') return '未登录或登录已过期'
  if (d === 'invalid token' || d === 'invalid token or expired token') return '无效的令牌'
  if (d === 'token expired') return '登录已过期，请重新登录'
  if (d.includes('credentials')) return '账号或密码错误'
  // 兜底：原文返回（不强行翻译，避免误伤）
  return ''
}
