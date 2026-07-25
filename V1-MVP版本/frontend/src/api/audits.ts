/**
 * 审核 API 客户端。
 */
import { api } from '@/utils/request'

export interface AuditItem {
  id: number
  activity_id: number
  theme: string
  location: string
  training_at: string
  participant_count: number
  study_hours: number
  organizer_branch_id: number
  organizer_branch_name: string | null
  community_id: number
  community_name: string | null
  submitter_id: number
  submitter_name: string | null
  current_node: string
  status: string
  created_at: string
}

export interface AuditListResponse {
  total: number
  items: AuditItem[]
}

export interface AuditLog {
  id: number
  activity_id: number
  node: string
  operator_id: number
  operator_name: string | null
  action: 'submit' | 'approve' | 'reject'
  comment: string | null
  created_at: string
}

export const auditsApi = {
  pending() {
    return api.get<AuditListResponse>('/audits/pending')
  },
  history(params: { page?: number; page_size?: number } = {}) {
    return api.get<AuditListResponse>('/audits/history', params)
  },
  approve(activityId: number, comment?: string) {
    return api.post<{ ok: boolean; activity_id: number; status: string }>(
      `/audits/${activityId}/approve`,
      { comment },
    )
  },
  reject(activityId: number, comment: string) {
    return api.post<{ ok: boolean; activity_id: number; status: string; reject_reason: string }>(
      `/audits/${activityId}/reject`,
      { comment },
    )
  },
  logs(activityId: number) {
    return api.get<AuditLog[]>(`/audits/${activityId}/logs`)
  },
}
