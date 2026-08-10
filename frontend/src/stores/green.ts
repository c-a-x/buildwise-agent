import { ref } from 'vue'
import { defineStore } from 'pinia'

import { getApiError } from '@/api/http'
import { greenApi } from '@/api/green'
import type { CarbonAnalysisResult, CarbonAnalysisSummary, EnvRecord, EnvThreshold, GreenAdvice, GreenAdviceForm, GreenAnalyzeForm, GreenAssessmentForm, GreenAssessmentResult, GreenAssessmentSummary, GreenFactor, GreenTarget, GreenTargetForm, GreenTrend } from '@/types/green'

export const useGreenStore = defineStore('green', () => {
  // 碳排核算
  const currentResult = ref<CarbonAnalysisResult | null>(null)
  const analyses = ref<CarbonAnalysisSummary[]>([])
  const factors = ref<GreenFactor[]>([])
  const analyzing = ref(false)
  const loadingList = ref(false)
  const loadingDetail = ref(false)
  const loadingFactors = ref(false)
  const error = ref('')

  // 四节一环保评估
  const currentAssessment = ref<GreenAssessmentResult | null>(null)
  const assessments = ref<GreenAssessmentSummary[]>([])
  const submittingAssessment = ref(false)
  const loadingAssessments = ref(false)
  const assessmentError = ref('')

  // 环保监测台账
  const envRecords = ref<EnvRecord[]>([])
  const envThresholds = ref<EnvThreshold[]>([])
  const savingEnvRecord = ref(false)
  const loadingEnvRecords = ref(false)
  const loadingEnvThresholds = ref(false)
  const envError = ref('')

  // 碳排趋势与目标
  const trend = ref<GreenTrend | null>(null)
  const target = ref<GreenTarget | null>(null)
  const loadingTrend = ref(false)
  const loadingTarget = ref(false)
  const savingTarget = ref(false)
  const trendError = ref('')

  // AI 优化建议
  const advice = ref<GreenAdvice | null>(null)
  const generatingAdvice = ref(false)
  const adviceError = ref('')

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

  async function submitAssessment(payload: GreenAssessmentForm): Promise<GreenAssessmentResult> {
    submittingAssessment.value = true
    assessmentError.value = ''
    try {
      currentAssessment.value = await greenApi.submitAssessment(payload)
      await loadAssessments(payload.project_id)
      return currentAssessment.value
    } catch (cause) {
      assessmentError.value = getApiError(cause)
      throw cause
    } finally {
      submittingAssessment.value = false
    }
  }

  async function loadAssessments(projectId?: string): Promise<void> {
    loadingAssessments.value = true
    assessmentError.value = ''
    try {
      assessments.value = await greenApi.assessments(projectId)
    } catch (cause) {
      assessmentError.value = getApiError(cause)
    } finally {
      loadingAssessments.value = false
    }
  }

  async function saveEnvRecord(payload: Parameters<typeof greenApi.saveEnvRecord>[0]): Promise<EnvRecord> {
    savingEnvRecord.value = true
    envError.value = ''
    try {
      const record = await greenApi.saveEnvRecord(payload)
      await loadEnvRecords({ project_id: payload.project_id })
      return record
    } catch (cause) {
      envError.value = getApiError(cause)
      throw cause
    } finally {
      savingEnvRecord.value = false
    }
  }

  async function loadEnvRecords(params?: Parameters<typeof greenApi.envRecords>[0]): Promise<void> {
    loadingEnvRecords.value = true
    envError.value = ''
    try {
      envRecords.value = await greenApi.envRecords(params)
    } catch (cause) {
      envError.value = getApiError(cause)
    } finally {
      loadingEnvRecords.value = false
    }
  }

  async function loadEnvThresholds(): Promise<void> {
    loadingEnvThresholds.value = true
    envError.value = ''
    try {
      envThresholds.value = await greenApi.envThresholds()
    } catch (cause) {
      envError.value = getApiError(cause)
    } finally {
      loadingEnvThresholds.value = false
    }
  }

  async function loadTrend(projectId: string): Promise<void> {
    loadingTrend.value = true
    trendError.value = ''
    try {
      trend.value = await greenApi.trend(projectId)
    } catch (cause) {
      trendError.value = getApiError(cause)
    } finally {
      loadingTrend.value = false
    }
  }

  async function loadTarget(projectId: string): Promise<void> {
    loadingTarget.value = true
    trendError.value = ''
    try {
      target.value = await greenApi.target(projectId)
    } catch (cause) {
      trendError.value = getApiError(cause)
    } finally {
      loadingTarget.value = false
    }
  }

  async function saveTarget(payload: GreenTargetForm): Promise<GreenTarget> {
    savingTarget.value = true
    trendError.value = ''
    try {
      target.value = await greenApi.saveTarget(payload)
      return target.value
    } catch (cause) {
      trendError.value = getApiError(cause)
      throw cause
    } finally {
      savingTarget.value = false
    }
  }

  async function generateAdvice(payload: GreenAdviceForm): Promise<GreenAdvice> {
    generatingAdvice.value = true
    adviceError.value = ''
    try {
      advice.value = await greenApi.advice(payload)
      return advice.value
    } catch (cause) {
      adviceError.value = getApiError(cause)
      throw cause
    } finally {
      generatingAdvice.value = false
    }
  }

  function clearResult(): void {
    currentResult.value = null
    currentAssessment.value = null
    advice.value = null
    error.value = ''
    assessmentError.value = ''
  }

  return {
    currentResult,
    analyses,
    factors,
    analyzing,
    loadingList,
    loadingDetail,
    loadingFactors,
    error,
    currentAssessment,
    assessments,
    submittingAssessment,
    loadingAssessments,
    assessmentError,
    envRecords,
    envThresholds,
    savingEnvRecord,
    loadingEnvRecords,
    loadingEnvThresholds,
    envError,
    trend,
    target,
    loadingTrend,
    loadingTarget,
    savingTarget,
    trendError,
    advice,
    generatingAdvice,
    adviceError,
    analyze,
    loadAnalyses,
    loadAnalysis,
    loadFactors,
    submitAssessment,
    loadAssessments,
    saveEnvRecord,
    loadEnvRecords,
    loadEnvThresholds,
    loadTrend,
    loadTarget,
    saveTarget,
    generateAdvice,
    clearResult,
  }
})
