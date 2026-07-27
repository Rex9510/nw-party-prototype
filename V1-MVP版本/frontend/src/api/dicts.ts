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
  // 讲师
  lecturers() {
    return api.get<Lecturer[]>('/dicts/lecturers')
  },
  createLecturer(name: string, intro?: string) {
    return api.post<Lecturer>('/dicts/lecturers', { name, intro })
  },
  updateLecturer(id: number, body: { name?: string; intro?: string; status?: string }) {
    return api.patch<Lecturer>(`/dicts/lecturers/${id}`, body)
  },
  deleteLecturer(id: number) {
    return api.delete(`/dicts/lecturers/${id}`)
  },

  // 培训对象类别
  trainingCategories() {
    return api.get<DictItem[]>('/dicts/training-categories')
  },
  createTrainingCategory(code: string, name: string, sort = 0) {
    return api.post<DictItem>('/dicts/training-categories', { code, name, sort })
  },
  updateTrainingCategory(id: number, body: { name?: string; sort?: number }) {
    return api.patch<DictItem>(`/dicts/training-categories/${id}`, body)
  },
  deleteTrainingCategory(id: number) {
    return api.delete(`/dicts/training-categories/${id}`)
  },

  // 培训来源
  trainingSources() {
    return api.get<DictItem[]>('/dicts/training-sources')
  },
  createTrainingSource(code: string, name: string, sort = 0) {
    return api.post<DictItem>('/dicts/training-sources', { code, name, sort })
  },
  updateTrainingSource(id: number, body: { name?: string; sort?: number }) {
    return api.patch<DictItem>(`/dicts/training-sources/${id}`, body)
  },
  deleteTrainingSource(id: number) {
    return api.delete(`/dicts/training-sources/${id}`)
  },
}
