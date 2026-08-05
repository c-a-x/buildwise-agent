import { ref } from 'vue'
import { defineStore } from 'pinia'

import { getApiError } from '@/api/http'
import { qualityApi, type QualityAnalyzePayload } from '@/api/quality'
import type { QualityAnalysisResult, QualityTaskSummary } from '@/types/quality'

export const useQualityStore = defineStore('quality', () => {
  const currentResult = ref<QualityAnalysisResult | null>(null)
  const tasks = ref<QualityTaskSummary[]>([])
  const analyzing = ref(false)
  const loadingTasks = ref(false)
  const loadingTask = ref(false)
  const error = ref('')

  async function analyze(file: File, payload: QualityAnalyzePayload): Promise<QualityAnalysisResult> {
    analyzing.value = true
    error.value = ''
    try {
      currentResult.value = await qualityApi.analyze(file, payload)
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
      tasks.value = await qualityApi.tasks(projectId)
    } catch (cause) {
      error.value = getApiError(cause)
    } finally {
      loadingTasks.value = false
    }
  }

  async function loadTask(taskId: string): Promise<QualityAnalysisResult> {
    loadingTask.value = true
    error.value = ''
    try {
      currentResult.value = await qualityApi.task(taskId)
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
