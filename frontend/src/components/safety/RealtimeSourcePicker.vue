<script setup lang="ts">
/** 实时检测视频源：演示模式（循环示例图）/ 本机摄像头（getUserMedia）。 */

import { computed, onMounted, onUnmounted, ref, watch } from 'vue'
import type { Ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import BoundingBoxOverlay from '@/components/safety/BoundingBoxOverlay.vue'
import sampleSiteMixed from '@/assets/samples/sample_site_mixed.jpg'
import sampleSiteNoHelmet from '@/assets/samples/sample_site_no_helmet.jpg'
import sampleSiteNoMask from '@/assets/samples/sample_site_no_mask.jpg'
import type { DetectFrameHazard } from '@/types/safety'

type SourceMode = 'demo' | 'camera'

const props = defineProps<{
  frameSource: Ref<HTMLImageElement | HTMLVideoElement | null>
  hazards: DetectFrameHazard[]
  alarmActive: boolean
  analyzing: boolean
  running: boolean
}>()

const mode = ref<SourceMode>('demo')
const cameraError = ref('')
const cameraStream = ref<MediaStream | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)
// 本机摄像头设备列表：getUserMedia 默认用系统"默认摄像头"（可能是 DroidCam 等虚拟设备），
// 需 enumerateDevices + deviceId 显式选择电脑本体的 USB/内置摄像头。
const cameraDevices = ref<MediaDeviceInfo[]>([])
const selectedCameraId = ref('')

const emit = defineEmits<{
  (e: 'source-change'): void
}>()

const modes: { key: SourceMode; label: string; icon: 'spark' | 'camera' }[] = [
  { key: 'demo', label: '演示模式', icon: 'spark' },
  { key: 'camera', label: '本机摄像头', icon: 'camera' },
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

let demoTimer: number | null = null

function bindSource(el: unknown): void {
  props.frameSource.value = (el as HTMLImageElement | HTMLVideoElement | null) ?? null
}

function bindVideoSource(el: unknown): void {
  const video = (el as HTMLVideoElement | null) ?? null
  videoEl.value = video
  // 本机摄像头也要纳入抓帧检测，否则 frameSource 残留上一源（演示图/空），画错框或干脆不检测
  props.frameSource.value = video
  attachStream()
}

function attachStream(): void {
  if (videoEl.value && cameraStream.value) videoEl.value.srcObject = cameraStream.value
}

async function refreshCameraDevices(): Promise<void> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameraDevices.value = devices.filter((device) => device.kind === 'videoinput')
  } catch {
    cameraDevices.value = []
  }
}

function deviceLabel(device: MediaDeviceInfo, index: number): string {
  return device.label || `摄像头 ${index + 1}`
}

async function startCamera(): Promise<void> {
  try {
    await refreshCameraDevices()
    const constraints: MediaTrackConstraints = { width: { ideal: 1280 }, height: { ideal: 720 } }
    if (selectedCameraId.value) constraints.deviceId = { exact: selectedCameraId.value }
    const stream = await navigator.mediaDevices.getUserMedia({ video: constraints })
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

async function selectCamera(deviceId: string): Promise<void> {
  if (deviceId === selectedCameraId.value) return
  selectedCameraId.value = deviceId
  if (mode.value !== 'camera') return
  stopCamera()
  await startCamera()
}

function onCameraSelect(event: Event): void {
  void selectCamera((event.target as HTMLSelectElement).value)
}

function stopCamera(): void {
  cameraStream.value?.getTracks().forEach((track) => track.stop())
  cameraStream.value = null
  if (videoEl.value) videoEl.value.srcObject = null
}

async function selectMode(next: SourceMode): Promise<void> {
  if (next === mode.value) return
  stopCamera()
  mode.value = next
  if (next === 'camera') await startCamera()
}

function cycleDemo(): void {
  demoIndex.value = (demoIndex.value + 1) % samples.length
}

watch(mode, (next) => {
  emit('source-change') // 切换视频源：父组件需清空上一源的检测结果
  if (demoTimer !== null) {
    window.clearInterval(demoTimer)
    demoTimer = null
  }
  if (next === 'demo') demoTimer = window.setInterval(cycleDemo, DEMO_INTERVAL_MS)
})

onMounted(() => {
  // 摄像头插拔/系统默认设备变化时刷新设备列表
  navigator.mediaDevices?.addEventListener('devicechange', refreshCameraDevices)
})

onUnmounted(() => {
  navigator.mediaDevices?.removeEventListener('devicechange', refreshCameraDevices)
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
        <video v-else :ref="bindVideoSource" autoplay playsinline muted alt="本机摄像头画面" />
        <BoundingBoxOverlay :hazards="props.hazards" />
        <div v-if="!running" class="stage-badge">已暂停</div>
        <div v-else-if="analyzing" class="stage-badge">检测中…</div>
      </div>

      <div v-if="mode === 'camera' && cameraError" class="stage-note error"><AppIcon name="info" :size="14" />{{ cameraError }}</div>
      <div v-else-if="mode === 'demo'" class="stage-note"><AppIcon name="spark" :size="14" />演示画面循环切换 · 当前：{{ demoName }}</div>
      <div v-else-if="mode === 'camera'" class="camera-field">
        <div class="stage-note"><AppIcon name="camera" :size="14" />本机摄像头画面仅在本浏览器内分析，不上传存储</div>
        <div v-if="cameraDevices.length > 1" class="camera-select">
          <label for="camera-device">视频设备</label>
          <select id="camera-device" :value="selectedCameraId" @change="onCameraSelect" aria-label="选择摄像头设备">
            <option value="">默认摄像头</option>
            <option v-for="(device, index) in cameraDevices" :key="device.deviceId" :value="device.deviceId">{{ deviceLabel(device, index) }}</option>
          </select>
        </div>
      </div>

    </div>
  </div>
</template>

<style scoped>
.source-picker { display: flex; flex-direction: column; gap: 12px; min-width: 0; }
.source-tabs { display: inline-flex; gap: 6px; }
.source-tab { display: inline-flex; align-items: center; gap: 6px; min-height: 44px; border: 1px solid var(--line); border-radius: 8px; padding: 0 12px; color: var(--text-soft); background: var(--surface); font-size: 12px; font-weight: 700; cursor: pointer; transition: border-color var(--ease), color var(--ease), background var(--ease); }
.source-tab:hover { border-color: var(--blue); color: var(--blue); }
.source-tab.active { border-color: var(--primary); color: var(--surface); background: var(--primary); }
.source-stage { position: relative; display: flex; flex-direction: column; gap: 10px; min-width: 0; }
.stage-media { position: relative; overflow: hidden; border: 1px solid var(--line); border-radius: 12px; background: var(--navy-950); aspect-ratio: 4 / 3; }
.stage-media img, .stage-media video { position: absolute; inset: 0; width: 100%; height: 100%; object-fit: contain; }
.source-stage.is-alarm .stage-media { border-color: var(--danger); animation: alarm-pulse 0.9s ease-in-out infinite; }
@keyframes alarm-pulse {
  0%, 100% { box-shadow: 0 0 0 3px var(--danger); }
  50% { box-shadow: inset 0 0 0 3px var(--danger); }
}
.stage-badge { position: absolute; top: 10px; right: 10px; z-index: 3; border-radius: 999px; padding: 3px 9px; color: var(--surface); background: var(--navy-950); font-size: 10px; font-weight: 800; }
.stage-note { display: flex; align-items: center; gap: 6px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.stage-note .app-icon { flex: none; color: var(--blue); }
.stage-note.error { color: var(--danger); }
.stage-note.error .app-icon { color: var(--danger); }
.camera-field { display: flex; flex-direction: column; gap: 8px; }
.camera-select { display: flex; align-items: center; gap: 8px; }
.camera-select label { flex: none; color: var(--muted); font-size: 11px; font-weight: 700; }
.camera-select select { flex: 1; min-width: 0; min-height: 44px; height: 44px; appearance: none; border: 1px solid var(--line); border-radius: 8px; padding: 0 42px 0 11px; color: var(--text); background-color: var(--surface); background-image: var(--select-chevron); background-position: right 12px center; background-repeat: no-repeat; background-size: 16px; font-size: 12px; }
.camera-select select:focus { outline: none; border-color: var(--blue); }
</style>
