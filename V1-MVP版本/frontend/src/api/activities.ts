/**
 * 培训活动 API 客户端。
 */
import { api } from '@/utils/request'

export interface Participant {
  id?: number
  member_id: number
  study_hours: number
  attendance_status: string
  member_name?: string | null
  member_phone?: string | null
  // v3: 参加人员所属组织（审核页回显用）
  member_org_level?: 'street' | 'community' | 'branch' | null
  member_branch_name?: string | null
  member_community_name?: string | null
  member_street_name?: string | null
}

export interface Attachment {
  id?: number
  kind: 'photo' | 'signin'
  file_url: string
  file_size?: number
  sort: number
}

export interface Activity {
  id: number
  // v3: organizer_branch_id nullable，前端不再用，仅作审计
  organizer_branch_id: number | null
  community_id: number
  training_at: string
  location: string
  lecturer_name: string | null
  lecturer_bio: string | null
  theme: string
  participant_count: number
  online_offline: 'online' | 'offline' | 'hybrid'
  is_centralized: boolean
  is_innovation_theory: boolean
  // v3: 兼容老数据，前端仍发，但展示用 organize_type
  source_type: 'upper_send' | 'self_organize' | null
  // v3: 举办方式（前端展示名 = 举办单位）
  organize_type: 'self_organize' | 'upper_send'
  // v3: 自行组织时的协办支部（1+）
  co_organize_branch_ids: number[]
  // v2: 培训对象多选
  audience_category: string[]
  study_hours: number | null
  status: 'draft' | 'pending_community' | 'pending_street' | 'approved' | 'rejected'
  reject_reason: string | null
  created_by: number
  created_at: string
  updated_at: string
  participants?: Participant[]
  attachments?: Attachment[]
  // v2 新增
  upper_org: string | null
  study_methods: string[]
}

export interface ActivityListItem {
  id: number
  organizer_branch_id: number | null
  community_id: number
  training_at: string
  location: string
  theme: string
  participant_count: number
  online_offline: string
  source_type: string | null
  // v3
  organize_type: 'self_organize' | 'upper_send'
  co_organize_branch_ids: number[]
  audience_category: string[]
  study_hours: number | null
  status: string
  created_at: string
  upper_org: string | null
  study_methods: string[]
}

export interface ActivityListResponse {
  total: number
  items: ActivityListItem[]
}

export const activitiesApi = {
  list(params: {
    page?: number
    page_size?: number
    status?: string
    community_id?: number
    branch_id?: number
    keyword?: string
  } = {}) {
    return api.get<ActivityListResponse>('/activities', params)
  },

  get(id: number) {
    return api.get<Activity>(`/activities/${id}`)
  },

  create(body: Partial<Activity> & { participants: Participant[]; photo_count: number }) {
    return api.post<Activity>('/activities', body)
  },

  update(id: number, body: Partial<Activity> & { participants?: Participant[] }) {
    return api.patch<Activity>(`/activities/${id}`, body)
  },

  remove(id: number) {
    return api.delete(`/activities/${id}`)
  },

  submit(id: number) {
    return api.post<Activity>(`/activities/${id}/submit`)
  },

  addAttachment(activityId: number, body: { kind: 'photo' | 'signin'; file_url: string; sort?: number }) {
    return api.post<Attachment>(`/activities/${activityId}/attachments`, body)
  },

  removeAttachment(activityId: number, attachmentId: number) {
    return api.delete(`/activities/${activityId}/attachments/${attachmentId}`)
  },
  clearAttachments(activityId: number, kind?: 'photo' | 'signin') {
    return api.delete(
      kind
        ? `/activities/${activityId}/attachments?kind=${kind}`
        : `/activities/${activityId}/attachments`,
    )
  },
}
