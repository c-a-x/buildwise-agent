import { ref } from 'vue'
import { defineStore } from 'pinia'

import { getApiError } from '@/api/http'
import { greenApi } from '@/api/green'
import type { CarbonAnalysisResult, CarbonAnalysisSummary, GreenAnalyzeForm, GreenFactor } from '@/types/green'

export const useGreenStore = defineStore('green', () => {
  const currentResult = ref<CarbonAnalysisResult | null>(null)
  const analyses = ref<CarbonAnalysisSummary[]>([])
  const factors = ref<GreenFactor[]>([])
  const analyzing = ref(false)
  const loadingList = ref(false)
  const loadingDetail = ref(false)
  const loadingFactors = ref(false)
  const error = ref('')

  async function analyze(payload: GreenAnalyzeForm): Promise<CarbonAnalysisResult> {
    analyzing.value = true
    error.value = ''
    try {
      currentResult.value = await greenApi.analyze(payload)
      return currentResult.value
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      analyzing.value = false
    }
  }

  async function loadAnalyses(projectId?: string): Promise<void> {
    loadingList.value = true
    error.value = ''
    try {
      analyses.value = await greenApi.analyses(projectId)
    } catch (cause) {
      error.value = getApiError(cause)
    } finally {
      loadingList.value = false
    }
  }

  async function loadAnalysis(analysisId: string): Promise<CarbonAnalysisResult> {
    loadingDetail.value = true
    error.value = ''
    try {
      currentResult.value = await greenApi.analysis(analysisId)
      return currentResult.value
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      loadingDetail.value = false
    }
  }

  async function loadFactors(): Promise<void> {
    loadingFactors.value = true
    error.value = ''
    try {
      factors.value = await greenApi.factors()
    } catch (cause) {
      error.value = getApiError(cause)
    } finally {
      loadingFactors.value = false
    }
  }

  function clearResult(): void {
    currentResult.value = null
    error.value = ''
  }

  return { currentResult, analyses, factors, analyzing, loadingList, loadingDetail, loadingFactors, error, analyze, loadAnalyses, loadAnalysis, loadFactors, clearResult }
})
