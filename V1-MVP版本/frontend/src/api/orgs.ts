/**
 * 组织架构 API 客户端。
 */
import { api } from '@/utils/request'

export interface Street { id: number; name: string }
export interface Community { id: number; street_id: number; name: string }
export interface Branch { id: number; community_id: number; name: string }

export interface StreetTreeNode extends Street {
  communities: (Community & { branches: Branch[] })[]
}

export const orgsApi = {
  streets() {
    return api.get<Street[]>('/orgs/streets')
  },
  createStreet(name: string) {
    return api.post<Street>('/orgs/streets', { name })
  },
  updateStreet(id: number, name: string) {
    return api.patch<Street>(`/orgs/streets/${id}`, { name })
  },
  deleteStreet(id: number) {
    return api.delete(`/orgs/streets/${id}`)
  },

  communities(street_id?: number) {
    return api.get<Community[]>('/orgs/communities', { street_id })
  },
  createCommunity(street_id: number, name: string) {
    return api.post<Community>('/orgs/communities', { street_id, name })
  },
  updateCommunity(id: number, name: string) {
    return api.patch<Community>(`/orgs/communities/${id}`, { name })
  },
  deleteCommunity(id: number) {
    return api.delete(`/orgs/communities/${id}`)
  },

  branches(community_id?: number) {
    return api.get<Branch[]>('/orgs/branches', { community_id })
  },
  createBranch(community_id: number, name: string) {
    return api.post<Branch>('/orgs/branches', { community_id, name })
  },
  updateBranch(id: number, name: string) {
    return api.patch<Branch>(`/orgs/branches/${id}`, { name })
  },
  deleteBranch(id: number) {
    return api.delete(`/orgs/branches/${id}`)
  },

  tree() {
    return api.get<StreetTreeNode[]>('/orgs/tree')
  },
}
