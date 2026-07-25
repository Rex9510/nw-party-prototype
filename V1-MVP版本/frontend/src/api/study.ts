/**
 * 学时档案 API 客户端。
 */
import { api } from '@/utils/request'

export interface StudyListItem {
  member_id: number
  member_name: string
  member_phone: string
  branch_name: string | null
  year: number
  total_hours: number
  activity_count: number
}

export interface StudyListResponse {
  year: number
  total_members: number
  items: StudyListItem[]
}

export interface StudyDetailItem {
  activity_id: number
  theme: string
  training_at: string
  location: string
  study_hours: number
  status: string
  attendance_status: string
}

export interface StudyDetailResponse {
  member_id: number
  member_name: string
  year: number
  total_hours: number
  activity_count: number
  items: StudyDetailItem[]
}

export const studyApi = {
  list(params: { year: number; community_id?: number; branch_id?: number }) {
    return api.get<StudyListResponse>('/study-hours', params)
  },
  me(year: number) {
    return api.get<StudyDetailResponse>('/study-hours/me', { year })
  },
  member(memberId: number, year: number) {
    return api.get<StudyDetailResponse>(`/study-hours/${memberId}`, { year })
  },
}
