/**
 * 培训活动 API 客户端。
 */
import { api } from '@/utils/request'

export interface Participant {
  id?: number
  member_id: number
  study_hours: number
  attendance_status: string
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
  organizer_branch_id: number
  community_id: number
  training_at: string
  location: string
  lecturer_id: number | null
  theme: string
  participant_count: number
  online_offline: 'online' | 'offline' | 'hybrid'
  is_centralized: boolean
  is_innovation_theory: boolean
  source_type: 'upper_send' | 'self_organize'
  audience_category: string
  study_hours: number
  status: 'draft' | 'pending_community' | 'pending_street' | 'approved' | 'rejected'
  reject_reason: string | null
  created_by: number
  created_at: string
  updated_at: string
  participants?: Participant[]
  attachments?: Attachment[]
}

export interface ActivityListItem {
  id: number
  organizer_branch_id: number
  community_id: number
  training_at: string
  location: string
  theme: string
  participant_count: number
  online_offline: string
  source_type: string
  audience_category: string
  study_hours: number
  status: string
  created_at: string
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
}
