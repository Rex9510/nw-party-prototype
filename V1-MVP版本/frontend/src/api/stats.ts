/**
 * 统计 API 客户端（年/月/日 三维度）
 */
import { api } from '@/utils/request'

export interface StatItem {
  label: string
  session_count: number
  participant_count: number
}

export interface StatsResponse {
  period: 'year' | 'month' | 'day'
  label: string
  items: StatItem[]
  total_sessions: number
  total_participants: number
}

export type Period = 'year' | 'month' | 'day'

export interface StatsQuery {
  period: Period
  year?: number
  month?: number
  day?: string  // YYYY-MM-DD
}

export const statsApi = {
  stats(q: StatsQuery) {
    const params: Record<string, any> = { period: q.period }
    if (q.year !== undefined) params.year = q.year
    if (q.month !== undefined) params.month = q.month
    if (q.day) params.day = q.day
    return api.get<StatsResponse>('/stats/stats', params)
  },
  // 兼容老接口
  yearly(year: number) {
    return api.get<StatsResponse>('/stats/yearly', { year })
  },
  exportUrl(q: StatsQuery, token: string) {
    const params = new URLSearchParams()
    params.set('period', q.period)
    if (q.year !== undefined) params.set('year', String(q.year))
    if (q.month !== undefined) params.set('month', String(q.month))
    if (q.day) params.set('day', q.day)
    params.set('access_token', token)
    return `/api/v1/stats/stats/export?${params.toString()}`
  },
  // 兼容老 URL（用 yearly 路径）
  exportYearlyUrl(year: number, token: string) {
    return `/api/v1/stats/yearly/export?year=${year}&access_token=${token}`
  },
}
