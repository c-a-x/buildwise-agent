import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { projectsApi } from '@/api/projects'
import { getApiError } from '@/api/http'
import type { Project } from '@/types/project'
import { getProjectId, setProjectId } from '@/utils/storage'

export const useProjectStore = defineStore('project', () => {
  const projects = ref<Project[]>([])
  const currentProjectId = ref<string | null>(getProjectId())
  const loading = ref(false)
  const error = ref('')
  const currentProject = computed(() => projects.value.find((project) => project.id === currentProjectId.value) ?? projects.value[0] ?? null)

  async function loadProjects(): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      projects.value = await projectsApi.list()
      if (!currentProjectId.value || !projects.value.some((project) => project.id === currentProjectId.value)) {
        const first = projects.value[0]
        currentProjectId.value = first?.id ?? null
        if (first) setProjectId(first.id)
      }
    } catch (cause) {
      error.value = getApiError(cause)
    } finally {
      loading.value = false
    }
  }

  function selectProject(projectId: string): void {
    currentProjectId.value = projectId
    setProjectId(projectId)
  }

  return { projects, currentProjectId, currentProject, loading, error, loadProjects, selectProject }
})
