import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { projectsApi } from '@/api/projects'
import { getApiError } from '@/api/http'
import type { Project, ProjectCreate } from '@/types/project'
import { getProjectId, setProjectId } from '@/utils/storage'

interface LoadProjectsOptions {
  rethrow?: boolean
}

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProjectId = ref<string | null>(getProjectId())
  const activeRequests = ref(0)
  const loading = computed(() => activeRequests.value > 0)
  const error = ref('')
  const currentProject = computed(() => projects.value.find((project) => project.id === currentProjectId.value) ?? projects.value[0] ?? null)

  function beginRequest(): void {
    activeRequests.value += 1
  }

  function endRequest(): void {
    activeRequests.value = Math.max(0, activeRequests.value - 1)
  }

  async function loadProjects(options: LoadProjectsOptions = {}): Promise<boolean> {
    beginRequest()
    error.value = ''
    try {
      projects.value = await projectsApi.list()
      if (!currentProjectId.value || !projects.value.some((project) => project.id === currentProjectId.value)) {
        const first = projects.value[0]
        currentProjectId.value = first?.id ?? null
        if (first) setProjectId(first.id)
      }
      return true
    } catch (cause) {
      error.value = getApiError(cause)
      if (options.rethrow) throw cause
      return false
    } finally {
      endRequest()
    }
  }

  async function createProject(payload: ProjectCreate): Promise<Project> {
    beginRequest()
    error.value = ''
    try {
      const created = await projectsApi.create(payload)
      await loadProjects({ rethrow: true })
      if (projects.value.some((project) => project.id === created.id)) selectProject(created.id)
      return created
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      endRequest()
    }
  }

  function selectProject(projectId: string): void {
    currentProjectId.value = projectId
    setProjectId(projectId)
  }

  return { projects, currentProjectId, currentProject, loading, error, loadProjects, createProject, selectProject }
})
