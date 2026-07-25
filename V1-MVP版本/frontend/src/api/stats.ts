/**
 * 统计 API 客户端。
 */
import { api } from '@/utils/request'

export interface StatItem {
  label: string
  session_count: number
  participant_count: number
}

export interface YearlyStatsResponse {
  year: number
  items: StatItem[]
  total_sessions: number
  total_participants: number
}

export const statsApi = {
  yearly(year: number) {
    return api.get<YearlyStatsResponse>('/stats/yearly', { year })
  },
  exportYearlyUrl(year: number, token: string) {
    return `/api/v1/stats/yearly/export?year=${year}&access_token=${token}`
  },
}
