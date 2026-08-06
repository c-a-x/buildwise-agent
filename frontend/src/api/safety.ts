import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { DetectFrameResult, SafetyAnalysisResult, SafetyTaskSummary } from '@/types/safety'

export interface SafetyAnalyzePayload {
  project_id: string
  location: string
  work_type: string
  description?: string
  demo_scenario?: string
}

export interface BroadcastTestResult {
  delivered: boolean
  message: string
  tts: { provider: string | null; available: boolean; is_simulated: boolean }
  reason: string | null
}

export const safetyApi = {
  async analyze(file: File, payload: SafetyAnalyzePayload): Promise<SafetyAnalysisResult> {
    const form = new FormData()
    form.append('image', file)
    Object.entries(payload).forEach(([key, value]) => {
      if (value) form.append(key, value)
    })
    const response = await http.post<ApiEnvelope<SafetyAnalysisResult>>('/safety/analyze', form)
    return response.data.data
  },
  async tasks(projectId?: string): Promise<SafetyTaskSummary[]> {
    const response = await http.get<ApiEnvelope<SafetyTaskSummary[]>>('/safety/tasks', { params: projectId ? { project_id: projectId } : {} })
    return response.data.data
  },
  async task(taskId: string): Promise<SafetyAnalysisResult> {
    const response = await http.get<ApiEnvelope<SafetyAnalysisResult>>(`/safety/tasks/${taskId}`)
    return response.data.data
  },
  // 实时单帧检测：只跑 YOLO、不落库。显式短超时，保证轮询不被 FormData 拦截器拖到 120s
  async detectFrame(file: Blob, timeoutMs = 10_000): Promise<DetectFrameResult> {
    const form = new FormData()
    form.append('image', file, 'frame.jpg')
    const response = await http.post<ApiEnvelope<DetectFrameResult>>('/safety/detect-frame', form, { timeout: timeoutMs })
    return response.data.data
  },
  // 语音广播测试：向配置的网络音响/PA webhook 推送一条测试播报，返回送达与 TTS 状态
  async broadcastTest(): Promise<BroadcastTestResult> {
    const response = await http.post<ApiEnvelope<BroadcastTestResult>>('/safety/broadcast-test')
    return response.data.data
  },
}
