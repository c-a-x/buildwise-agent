import { ref } from 'vue'
import { defineStore } from 'pinia'

import { getApiError } from '@/api/http'
import { safetyApi, type SafetyAnalyzePayload } from '@/api/safety'
import type { SafetyAnalysisResult, SafetyTaskSummary } from '@/types/safety'

export const useSafetyStore = defineStore('safety', () => {
  const currentResult = ref<SafetyAnalysisResult | null>(null)
  const tasks = ref<SafetyTaskSummary[]>([])
  const analyzing = ref(false)
  const loadingTasks = ref(false)
  const loadingTask = ref(false)
  const error = ref('')

  async function analyze(file: File, payload: SafetyAnalyzePayload): Promise<SafetyAnalysisResult> {
    analyzing.value = true
    error.value = ''
    try {
      currentResult.value = await safetyApi.analyze(file, payload)
      return currentResult.value
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      analyzing.value = false
    }
  }

  async function loadTasks(projectId?: string): Promise<void> {
    loadingTasks.value = true
    error.value = ''
    try {
      tasks.value = await safetyApi.tasks(projectId)
    } catch (cause) {
      error.value = getApiError(cause)
    } finally {
      loadingTasks.value = false
    }
  }

  async function loadTask(taskId: string): Promise<SafetyAnalysisResult> {
    loadingTask.value = true
    error.value = ''
    try {
      currentResult.value = await safetyApi.task(taskId)
      return currentResult.value
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      loadingTask.value = false
    }
  }

  function clearResult(): void {
    currentResult.value = null
    error.value = ''
  }

  return { currentResult, tasks, analyzing, loadingTasks, loadingTask, error, analyze, loadTasks, loadTask, clearResult }
})
