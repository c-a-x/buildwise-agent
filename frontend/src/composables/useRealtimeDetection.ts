/** 实时检测：canvas 抓帧 → detect-frame 轮询（setTimeout 链防重叠）。 */

import { onUnmounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { safetyApi } from '@/api/safety'
import type { DetectFrameResult } from '@/types/safety'

const FRAME_INTERVAL_MS = 1000

export function useRealtimeDetection() {
  const frameSource = ref<HTMLImageElement | HTMLVideoElement | null>(null)
  const analyzing = ref(false)
  const running = ref(false)
  const error = ref('')
  const lastResult = ref<DetectFrameResult | null>(null)
  const framesAnalyzed = ref(0)
  const lastLatencyMs = ref<number | null>(null)

  const canvas = document.createElement('canvas')
  let timerId: number | null = null
  let stopped = false

  function captureBlob(): Promise<Blob | null> {
    const source = frameSource.value
    if (!source) return Promise.resolve(null)
    // 视频需等元数据就绪、图片需等加载完成，否则跳过本帧（避免抓空白帧）
    if (source instanceof HTMLImageElement) {
      if (!source.complete || !source.naturalWidth || !source.naturalHeight) return Promise.resolve(null)
    } else if (!(source as HTMLVideoElement).videoWidth || !(source as HTMLVideoElement).videoHeight) {
      return Promise.resolve(null)
    }
    const width = (source as HTMLVideoElement).videoWidth || (source as HTMLImageElement).naturalWidth
    const height = (source as HTMLVideoElement).videoHeight || (source as HTMLImageElement).naturalHeight
    if (!width || !height) return Promise.resolve(null)
    canvas.width = width
    canvas.height = height
    const ctx = canvas.getContext('2d')
    if (!ctx) return Promise.resolve(null)
    ctx.drawImage(source, 0, 0, width, height)
    try {
      return new Promise<Blob | null>((resolve) =>
        canvas.toBlob((blob) => resolve(blob), 'image/jpeg', 0.8),
      )
    } catch {
      // Browser camera security can still taint frames in some environments.
      error.value = '视频帧抓取被浏览器安全策略阻止；已切换为仅显示不检测。'
      return Promise.resolve(null)
    }
  }

  async function tick(): Promise<void> {
    if (stopped) {
      schedule()
      return
    }
    const blob = await captureBlob()
    if (stopped) return
    if (!blob) {
      schedule()
      return
    }
    analyzing.value = true
    try {
      const result = await safetyApi.detectFrame(blob)
      if (stopped) return
      lastResult.value = result
      lastLatencyMs.value = result.latency_ms
      framesAnalyzed.value += 1
      error.value = result.available ? '' : (result.message || '实时检测模型不可用')
    } catch (cause) {
      if (!stopped) error.value = getApiError(cause)
    } finally {
      analyzing.value = false
      schedule()
    }
  }

  function schedule(): void {
    if (stopped) return
    timerId = window.setTimeout(() => void tick(), FRAME_INTERVAL_MS)
  }

  function start(): void {
    if (running.value) return
    stopped = false
    running.value = true
    error.value = ''
    schedule()
  }

  function stop(): void {
    stopped = true
    running.value = false
    if (timerId !== null) {
      clearTimeout(timerId)
      timerId = null
    }
  }

  /** 切换视频源时清空上一源的检测结果，避免旧检测框残留；不打断检测循环。 */
  function reset(): void {
    lastResult.value = null
    lastLatencyMs.value = null
    framesAnalyzed.value = 0
    error.value = ''
  }

  onUnmounted(stop)

  return {
    frameSource,
    analyzing,
    running,
    error,
    lastResult,
    framesAnalyzed,
    lastLatencyMs,
    start,
    stop,
    reset,
  }
}
