/**
 * 党员库 API 客户端。
 */
import { api } from '@/utils/request'

export interface MemberItem {
  id: number
  name: string
  phone: string
  id_card_no: string | null
  gender: string | null
  join_date: string | null
  status: string
  branch_id: number
  branch_name: string | null
  created_at: string
  updated_at: string
}

export interface MemberListResponse {
  total: number
  items: MemberItem[]
}

export interface MemberCreateBody {
  name: string
  phone: string
  id_card_no?: string
  gender?: 'male' | 'female' | 'other'
  join_date?: string
  branch_id: number
}

export const membersApi = {
  list(params: {
    page?: number
    page_size?: number
    branch_id?: number
    community_id?: number
    keyword?: string
    status?: string
  } = {}) {
    return api.get<MemberListResponse>('/members', params)
  },

  get(id: number) {
    return api.get<MemberItem>(`/members/${id}`)
  },

  create(body: MemberCreateBody) {
    return api.post<MemberItem>('/members', body)
  },

  update(id: number, body: Partial<MemberCreateBody>) {
    return api.patch<MemberItem>(`/members/${id}`, body)
  },

  remove(id: number) {
    return api.delete(`/members/${id}`)
  },
}
