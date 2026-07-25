/**
 * 组织架构 API 客户端。
 */
import { api } from '@/utils/request'

export interface Street { id: number; name: string }
export interface Community { id: number; street_id: number; name: string }
export interface Branch { id: number; community_id: number; name: string }

export const orgsApi = {
  streets() {
    return api.get<Street[]>('/orgs/streets')
  },
  communities(street_id?: number) {
    return api.get<Community[]>('/orgs/communities', { street_id })
  },
  branches(community_id?: number) {
    return api.get<Branch[]>('/orgs/branches', { community_id })
  },
  tree() {
    return api.get<any[]>('/orgs/tree')
  },
}
