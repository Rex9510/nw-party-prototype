/**
 * 人员管理库 API 客户端。
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
  org_level: 'street' | 'community' | 'branch'
  branch_id: number | null
  branch_name: string | null
  community_id: number | null
  community_name: string | null
  street_id: number | null
  street_name: string | null
  roles: string[]
  identities: string[]
  photo_urls: string[]
  is_mobile_member: boolean
  flow_in_date: string | null
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
  gender?: 'male' | 'female'
  join_date?: string
  branch_id: number
  roles?: string[]
  identities?: string[]
  photo_urls?: string[]  // 最多 5 张 dataURL
  is_mobile_member?: boolean
  flow_in_date?: string | null  // is_mobile_member=true 时必填
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

  /** 通过手机号查党员（"我的"页面用）。 */
  getByPhone(phone: string) {
    return api.get<MemberItem>(`/members/by-phone/${phone}`)
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
