<script setup lang="ts">
/**
 * 相机拍照：打开摄像头预览，拍摄单帧转成 JPEG File 并 emit `captured`。
 * 复用实时监控页 getUserMedia + 设备选择模式；画面仅在本浏览器内处理，
 * 生成的图片直接喂给父组件已有的 acceptFile / 分析接口，不额外存储。
 */
import { computed, onMounted, onUnmounted, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'

withDefaults(defineProps<{ disabled?: boolean; label?: string }>(), {
  disabled: false,
  label: '相机拍照',
})

const emit = defineEmits<{
  (e: 'captured', file: File): void
}>()

const open = ref(false)
const starting = ref(false)
const error = ref('')
const stream = ref<MediaStream | null>(null)
const videoEl = ref<HTMLVideoElement | null>(null)
const cameraDevices = ref<MediaDeviceInfo[]>([])
const selectedCameraId = ref('')

const canCapture = computed(() => Boolean(stream.value) && !starting.value && !error.value)

function deviceLabel(device: MediaDeviceInfo, index: number): string {
  return device.label || `摄像头 ${index + 1}`
}

function stopCamera(): void {
  stream.value?.getTracks().forEach((track) => track.stop())
  stream.value = null
  if (videoEl.value) videoEl.value.srcObject = null
}

function attachStream(): void {
  if (videoEl.value && stream.value) videoEl.value.srcObject = stream.value
}

// 视频元素挂载时绑定模板 ref 并挂上已就绪的流（避免异步竞态）
function bindVideo(el: unknown): void {
  videoEl.value = (el as HTMLVideoElement | null) ?? null
  attachStream()
}

async function refreshCameraDevices(): Promise<void> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    cameraDevices.value = devices.filter((device) => device.kind === 'videoinput')
  } catch {
    cameraDevices.value = []
  }
}

async function startCamera(): Promise<void> {
  error.value = ''
  starting.value = true
  try {
    await refreshCameraDevices()
    const constraints: MediaTrackConstraints = { width: { ideal: 1280 }, height: { ideal: 720 } }
    if (selectedCameraId.value) constraints.deviceId = { exact: selectedCameraId.value }
    stream.value = await navigator.mediaDevices.getUserMedia({ video: constraints })
    attachStream()
  } catch (cause) {
    error.value =
      cause instanceof DOMException && cause.name === 'NotAllowedError'
        ? '摄像头权限被拒绝，请在浏览器地址栏允许摄像头访问后重试'
        : '无法打开摄像头，请确认已连接 USB 摄像头且未被其他程序占用'
  } finally {
    starting.value = false
  }
}

async function selectCamera(deviceId: string): Promise<void> {
  if (deviceId === selectedCameraId.value) return
  selectedCameraId.value = deviceId
  stopCamera()
  await startCamera()
}

function onCameraSelect(event: Event): void {
  void selectCamera((event.target as HTMLSelectElement).value)
}

async function openModal(): Promise<void> {
  open.value = true
  await startCamera()
}

function closeModal(): void {
  open.value = false
  stopCamera()
}

function capture(): void {
  const video = videoEl.value
  if (!video || !video.videoWidth) return
  const canvas = document.createElement('canvas')
  canvas.width = video.videoWidth
  canvas.height = video.videoHeight
  const context = canvas.getContext('2d')
  if (!context) return
  context.drawImage(video, 0, 0, canvas.width, canvas.height)
  canvas.toBlob((blob) => {
    if (!blob) return
    const file = new File([blob], `camera-${Date.now()}.jpg`, { type: 'image/jpeg' })
    emit('captured', file)
    closeModal()
  }, 'image/jpeg', 0.92)
}

onMounted(() => {
  // 摄像头插拔/系统默认设备变化时刷新设备列表
  navigator.mediaDevices?.addEventListener('devicechange', refreshCameraDevices)
})

onUnmounted(() => {
  navigator.mediaDevices?.removeEventListener('devicechange', refreshCameraDevices)
  stopCamera()
})
</script>

<template>
  <div class="camera-capture">
    <button type="button" class="secondary-button button-small capture-trigger" :disabled="disabled" @click="openModal">
      <AppIcon name="camera" :size="15" />{{ label }}
    </button>

    <Teleport to="body">
      <div v-if="open" class="capture-overlay" role="dialog" aria-modal="true" aria-label="相机拍照">
        <div class="capture-dialog">
          <header class="capture-head">
            <div><p class="section-kicker">CAMERA</p><h3>相机拍照</h3></div>
            <button type="button" class="icon-button" aria-label="关闭相机" @click="closeModal"><AppIcon name="close" :size="16" /></button>
          </header>
          <div class="capture-stage">
            <video :ref="bindVideo" autoplay playsinline muted alt="摄像头预览画面" />
            <div v-if="starting" class="capture-empty"><AppIcon name="camera" :size="26" /><span>正在打开摄像头…</span></div>
            <div v-else-if="error" class="capture-empty error"><AppIcon name="info" :size="26" /><span>{{ error }}</span></div>
          </div>
          <div v-if="!error && !starting && cameraDevices.length > 1" class="capture-select">
            <label for="capture-device">视频设备</label>
            <select id="capture-device" :value="selectedCameraId" @change="onCameraSelect">
              <option value="">默认摄像头</option>
              <option v-for="(device, index) in cameraDevices" :key="device.deviceId" :value="device.deviceId">{{ deviceLabel(device, index) }}</option>
            </select>
          </div>
          <p class="capture-note"><AppIcon name="info" :size="14" />拍摄的照片仅用于本次分析，在本浏览器内处理后直接提交，不会额外存储。</p>
          <footer class="capture-foot">
            <button type="button" class="primary-button" :disabled="!canCapture" @click="capture"><AppIcon name="camera" :size="15" />拍摄</button>
            <button type="button" class="secondary-button" @click="closeModal">取消</button>
          </footer>
        </div>
      </div>
    </Teleport>
  </div>
</template>

<style scoped>
.camera-capture { display: block; margin-top: 8px; }
.capture-trigger { width: 100%; }
.capture-overlay { position: fixed; inset: 0; z-index: 200; display: grid; place-items: center; padding: 20px; background: rgb(7 16 31 / 55%); backdrop-filter: blur(3px); }
.capture-dialog { width: min(100%, 480px); border: 1px solid var(--line); border-radius: 14px; padding: 20px; background: #fff; box-shadow: var(--shadow-lg); }
.capture-head { display: flex; align-items: flex-start; justify-content: space-between; gap: 12px; margin-bottom: 14px; }
.capture-head h3 { font-size: 16px; }
.capture-stage { position: relative; overflow: hidden; border: 1px solid var(--line); border-radius: 11px; background: #0e1424; aspect-ratio: 4 / 3; }
.capture-stage video { display: block; width: 100%; height: 100%; object-fit: contain; }
.capture-empty { position: absolute; inset: 0; display: grid; place-items: center; align-content: center; gap: 9px; color: #8aa2bd; font-size: 12px; }
.capture-empty .app-icon { color: #5a7ea8; }
.capture-empty.error { color: var(--danger); }
.capture-empty.error .app-icon { color: var(--danger); }
.capture-select { display: flex; align-items: center; gap: 8px; margin-top: 10px; }
.capture-select label { flex: none; color: var(--muted); font-size: 11px; font-weight: 700; }
.capture-select select { flex: 1; min-width: 0; height: 34px; border: 1px solid var(--line); border-radius: 8px; padding: 0 11px; color: var(--text); background: #fff; font-size: 12px; }
.capture-select select:focus { outline: none; border-color: var(--blue); }
.capture-note { display: flex; align-items: flex-start; gap: 7px; margin-top: 11px; color: var(--muted); font-size: 11px; line-height: 1.5; }
.capture-note .app-icon { flex: none; margin-top: 1px; color: var(--blue); }
.capture-foot { display: flex; justify-content: flex-end; gap: 9px; margin-top: 16px; }
</style>
