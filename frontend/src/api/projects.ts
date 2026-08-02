import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { Project } from '@/types/project'

export const projectsApi = {
  async list(): Promise<Project[]> {
    const response = await http.get<ApiEnvelope<Project[]>>('/projects')
    return response.data.data
  },
}
