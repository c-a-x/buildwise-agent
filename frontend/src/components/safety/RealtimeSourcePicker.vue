<script setup lang="ts">
/** 实时检测视频源：演示模式（循环示例图）/ 本机摄像头（getUserMedia）/ ESP32-CAM（MJPG 代理流）。 */

import { computed, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import BoundingBoxOverlay from '@/components/safety/BoundingBoxOverlay.vue'
import sampleSiteMixed from '@/assets/samples/sample_site_mixed.jpg'
import sampleSiteNoHelmet from '@/assets/samples/sample_site_no_helmet.jpg'
import sampleSiteNoMask from '@/assets/samples/sample_site_no_mask.jpg'
import { useAuthStore } from '@/stores/auth'
import type { DetectFrameHazard } from '@/types/safety'

type SourceMode = 'demo' | 'camera' | 'esp32'

const props = defineProps<{
  frameSource: Ref<HTMLImageElement | HTMLVideoElement | null>
  hazards: DetectFrameHazard[]
  alarmActive: boolean
  analyzing: boolean
  running: boolean
}>()

const auth = useAuthStore()
const mode = ref<SourceMode>('demo')
const cameraError = ref('')
const cameraStream = ref<MediaStream | null>(null)
const imageError = ref('')
const videoEl = ref<HTMLVideoElement | null>(null)

const modes: { key: SourceMode; label: string; icon: 'spark' | 'camera' | 'shield' }[] = [
  { key: 'demo', label: '演示模式', icon: 'spark' },
  { key: 'camera', label: '本机摄像头', icon: 'camera' },
  { key: 'esp32', label: 'ESP32-CAM', icon: 'shield' },
]

const samples = [
  { url: sampleSiteMixed, name: '三类违规混合' },
  { url: sampleSiteNoHelmet, name: '未戴安全帽' },
  { url: sampleSiteNoMask, name: '未戴口罩' },
]
const DEMO_INTERVAL_MS = 6000
const demoIndex = ref(0)
const currentSample = computed(() => samples[demoIndex.value % samples.length])
const demoUrl = computed(() => currentSample.value?.url ?? '')
const demoName = computed(() => currentSample.value?.name ?? '')

const esp32Url = ref('http://192.168.1.100:81/stream')
const proxiedUrl = computed(() => {
  const trimmed = esp32Url.value.trim()
  if (!trimmed) return ''
  const base = (import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1').replace(/\/api\/v1\/?$/, '')
  const params = new URLSearchParams({ url: trimmed, token: auth.token || '' })
  // token 走 query 仅为本地演示工具可接受（<img> 无法带 Authorization 头）
  return `${base}/api/v1/safety/mjpeg-proxy?${params.toString()}`
})

let demoTimer: number | null = null

function bindSource(el: unknown): void {
  props.frameSource.value = (el as HTMLImageElement | HTMLVideoElement | null) ?? null
}

function bindVideoSource(el: unknown): void {
  videoEl.value = (el as HTMLVideoElement | null) ?? null
  attachStream()
}

function attachStream(): void {
  if (videoEl.value && cameraStream.value) videoEl.value.srcObject = cameraStream.value
}

async function startCamera(): Promise<void> {
  try {
    const stream = await navigator.mediaDevices.getUserMedia({ video: { width: { ideal: 1280 }, height: { ideal: 720 } } })
    cameraStream.value = stream
    attachStream()
  } catch (cause) {
    cameraError.value =
      cause instanceof DOMException && cause.name === 'NotAllowedError'
        ? '摄像头权限被拒绝，请在浏览器地址栏允许摄像头访问后重试'
        : '无法打开摄像头，请确认已连接 USB 摄像头且未被其他程序占用'
    mode.value = 'demo'
  }
}

function stopCamera(): void {
  cameraStream.value?.getTracks().forEach((track) => track.stop())
  cameraStream.value = null
  if (videoEl.value) videoEl.value.srcObject = null
}

async function selectMode(next: SourceMode): Promise<void> {
  imageError.value = ''
  if (next === mode.value) return
  stopCamera()
  mode.value = next
  if (next === 'camera') await startCamera()
}

function cycleDemo(): void {
  demoIndex.value = (demoIndex.value + 1) % samples.length
}

watch(mode, (next) => {
  if (demoTimer !== null) {
    window.clearInterval(demoTimer)
    demoTimer = null
  }
  if (next === 'demo') demoTimer = window.setInterval(cycleDemo, DEMO_INTERVAL_MS)
})

onUnmounted(() => {
  if (demoTimer !== null) window.clearInterval(demoTimer)
  stopCamera()
})
</script>

<template>
  <div class="source-picker">
    <div class="source-tabs">
      <button v-for="item in modes" :key="item.key" type="button" class="source-tab" :class="{ active: mode === item.key }" @click="selectMode(item.key)">
        <AppIcon :name="item.icon" :size="15" /><span>{{ item.label }}</span>
      </button>
    </div>

    <div class="source-stage" :class="{ 'is-alarm': alarmActive }">
      <div class="stage-media">
        <img v-if="mode === 'demo'" :ref="bindSource" :src="demoUrl" crossorigin="anonymous" alt="演示现场画面" />
        <video v-else-if="mode === 'camera'" :ref="bindVideoSource" autoplay playsinline muted alt="本机摄像头画面" />
        <img v-else :ref="bindSource" :src="proxiedUrl" crossorigin="anonymous" alt="ESP32-CAM 实时画面" @error="() => (imageError = '无法连接摄像头，请检查 IP 与 MJPEG 固件')" @load="() => (imageError = '')" />
        <BoundingBoxOverlay :hazards="props.hazards" />
        <div v-if="!running" class="stage-badge">已暂停</div>
        <div v-else-if="analyzing" class="stage-badge">检测中…</div>
      </div>

      <div v-if="mode === 'camera' && cameraError" class="stage-note error"><AppIcon name="info" :size="14" />{{ cameraError }}</div>
      <div v-else-if="mode === 'esp32' && imageError" class="stage-note error"><AppIcon name="info" :size="14" />{{ imageError }}</div>
      <div v-else-if="mode === 'demo'" class="stage-note"><AppIcon name="spark" :size="14" />演示画面循环切换 · 当前：{{ demoName }}</div>
      <div v-else-if="mode === 'esp32'" class="stage-note"><AppIcon name="shield" :size="14" />经后端代理接入 {{ esp32Url.trim() || '未填写地址' }}</div>
      <div v-else class="stage-note"><AppIcon name="camera" :size="14" />本机摄像头画面仅在本浏览器内分析，不上传存储</div>

      <div v-if="mode === 'esp32'" class="esp32-field">
        <input v-model.trim="esp32Url" type="url" spellcheck="false" placeholder="http://192.168.1.100:81/stream" aria-label="ESP32-CAM MJPG 流地址" />
        <span class="mono">MJPG stream</span>
      </div>
    </div>
  </div>
</template>

<style scoped>
.source-picker { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.source-tabs { display: inline-flex; gap: 6px; }
.source-tab { display: inline-flex; align-items: center; gap: 6px; min-height: 30px; border: 1px solid var(--line); border-radius: 8px; padding: 0 12px; color: var(--text-soft); background: #fff; font-size: 12px; font-weight: 700; cursor: pointer; transition: border-color var(--ease), color var(--ease), background var(--ease); }
.source-tab:hover { border-color: var(--blue); color: var(--blue); }
.source-tab.active { border-color: var(--blue); color: #fff; background: var(--blue); }
.source-stage { position: relative; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.stage-media { position: relative; overflow: hidden; border: 1px solid var(--line); border-radius: 12px; background: #0e1424; aspect-ratio: 4 / 3; }
.stage-media img, .stage-media video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.source-stage.is-alarm .stage-media { border-color: var(--danger); animation: alarm-pulse 0.9s ease-in-out infinite; }
@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 3px var(--danger); }
  50% { box-shadow: 0 0 0 8px rgba(220, 53, 69, 0.25); }
}
.stage-badge { position: absolute; top: 10px; right: 10px; z-index: 3; border-radius: 999px; padding: 3px 9px; color: #fff; background: rgba(14, 20, 36, 0.72); font-size: 10px; font-weight: 800; }
.stage-note { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.stage-note .app-icon { flex: none; color: var(--blue); }
.stage-note.error { color: var(--danger); }
.stage-note.error .app-icon { color: var(--danger); }
.esp32-field { display: flex; align-items: center; gap: 8px; }
.esp32-field input { flex: 1; min-width: 0; height: 34px; border: 1px solid var(--line); border-radius: 8px; padding: 0 11px; color: var(--text); background: #fff; font-size: 12px; font-family: ui-monospace, "SFMono-Regular", Consolas, monospace; }
.esp32-field input:focus { outline: none; border-color: var(--blue); }
</style>
