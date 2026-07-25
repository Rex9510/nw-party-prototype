/**
 * 字典 API 客户端。
 */
import { api } from '@/utils/request'

export interface Lecturer {
  id: number
  name: string
  intro: string | null
  status: string
}

export interface DictItem {
  id: number
  code: string
  name: string
  sort: number
}

export const dictsApi = {
  lecturers() {
    return api.get<Lecturer[]>('/dicts/lecturers')
  },
  createLecturer(body: { name: string; intro?: string }) {
    return api.post<Lecturer>('/dicts/lecturers', body)
  },
  updateLecturer(id: number, body: Partial<{ name: string; intro: string; status: string }>) {
    return api.patch<Lecturer>(`/dicts/lecturers/${id}`, body)
  },

  trainingCategories() {
    return api.get<DictItem[]>('/dicts/training-categories')
  },
  trainingSources() {
    return api.get<DictItem[]>('/dicts/training-sources')
  },
}
