<script setup lang="ts">
/**
 * 工友助手语音输入：
 * - 优先浏览器 Web Speech API（SpeechRecognition，zh-CN）本地识别，无需后端、无需配置；
 * - 浏览器不支持时降级为 MediaRecorder 录音上传 POST /worker-care/transcribe（后端预留可插拔 ASR Provider）。
 * 识别/转写文字通过 emit('text') 上抛，由父组件填入输入框。
 */

import { computed, onUnmounted, ref } from 'vue'

import { getApiError } from '@/api/http'
import { workerCareApi } from '@/api/workerCare'
import AppIcon from '@/components/common/AppIcon.vue'

type VoiceState = 'idle' | 'recording' | 'transcribing' | 'error'

interface SpeechRecognitionLike {
  lang: string
  interimResults: boolean
  continuous: boolean
  start: () => void
  stop: () => void
  abort?: () => void
  onresult: ((event: { resultIndex: number; results: ArrayLike<{ isFinal: boolean; 0: { transcript: string } }> }) => void) | null
  onend: (() => void) | null
  onerror: ((event: { error?: string }) => void) | null
}

declare global {
  interface Window {
    SpeechRecognition?: new () => SpeechRecognitionLike
    webkitSpeechRecognition?: new () => SpeechRecognitionLike
  }
}

const props = defineProps<{ projectId: string; disabled?: boolean }>()
const emit = defineEmits<{ (e: 'text', value: string): void }>()

const state = ref<VoiceState>('idle')
const error = ref('')
const interim = ref('')
const audioDevices = ref<MediaDeviceInfo[]>([])
const selectedDeviceId = ref('')

let stream: MediaStream | null = null
let recognition: SpeechRecognitionLike | null = null
let recorder: MediaRecorder | null = null
const chunks: Blob[] = []
let finalText = ''

const buttonLabel = computed(() => ({ idle: '开始语音', recording: '停止', transcribing: '转写中…', error: '重试' })[state.value] ?? '开始语音')

function recognitionSupported(): boolean {
  return Boolean(window.SpeechRecognition || window.webkitSpeechRecognition)
}

async function refreshAudioDevices(): Promise<void> {
  try {
    const devices = await navigator.mediaDevices.enumerateDevices()
    audioDevices.value = devices.filter((device) => device.kind === 'audioinput')
  } catch {
    audioDevices.value = []
  }
}

function deviceLabel(device: MediaDeviceInfo, index: number): string {
  return device.label || `麦克风 ${index + 1}`
}

function stopTracks(): void {
  stream?.getTracks().forEach((track) => track.stop())
  stream = null
}

function finish(text: string): void {
  recognition = null
  stopTracks()
  state.value = 'idle'
  if (text.trim()) emit('text', text.trim())
}

function onRecognize(event: Parameters<NonNullable<SpeechRecognitionLike['onresult']>>[0]): void {
  let interimText = ''
  for (let i = event.resultIndex; i < event.results.length; i++) {
    const result = event.results[i]
    if (!result) continue
    const transcript = result[0]?.transcript ?? ''
    if (result.isFinal) finalText += transcript
    else interimText += transcript
  }
  interim.value = (finalText + interimText).trim()
}

function startRecognition(): void {
  const Recognition = window.SpeechRecognition || window.webkitSpeechRecognition
  if (!Recognition) return
  recognition = new Recognition()
  recognition.lang = 'zh-CN'
  recognition.interimResults = true
  recognition.continuous = true
  recognition.onresult = onRecognize
  recognition.onerror = (event) => {
    if (event.error === 'not-allowed') error.value = '麦克风权限被拒绝，请在浏览器地址栏允许麦克风访问后重试'
    else if (event.error === 'no-speech') error.value = '未听到声音，请靠近麦克风后重试'
    else if (event.error === 'network') error.value = '语音识别网络不可用，可改用文本输入'
  }
  recognition.onend = () => finish(finalText)
  recognition.start()
}

function startRecorder(): void {
  if (!stream) return
  recorder = new MediaRecorder(stream)
  recorder.ondataavailable = (event) => {
    if (event.data.size > 0) chunks.push(event.data)
  }
  recorder.onstop = () => {
    void transcribeUpload()
  }
  recorder.start()
}

async function transcribeUpload(): Promise<void> {
  const blob = new Blob(chunks, { type: recorder?.mimeType || 'audio/webm' })
  chunks.length = 0
  recorder = null
  stopTracks()
  state.value = 'transcribing'
  try {
    const result = await workerCareApi.transcribe(props.projectId, blob)
    if (result.available) {
      emit('text', result.text.trim())
      state.value = 'idle'
    } else {
      error.value = result.reason || '语音转写未配置，请改用文本输入'
      state.value = 'error'
    }
  } catch (cause) {
    error.value = getApiError(cause)
    state.value = 'error'
  }
}

async function start(): Promise<void> {
  if (props.disabled) return
  error.value = ''
  interim.value = ''
  finalText = ''
  chunks.length = 0
  state.value = 'recording'
  await refreshAudioDevices()
  if (recognitionSupported()) {
    // Web Speech 自带音频采集；设备下拉仅对后端转写（MediaRecorder）路径生效
    startRecognition()
    return
  }
  const constraints: MediaTrackConstraints = {}
  if (selectedDeviceId.value) constraints.deviceId = { exact: selectedDeviceId.value }
  try {
    stream = await navigator.mediaDevices.getUserMedia({ audio: constraints })
  } catch (cause) {
    error.value =
      cause instanceof DOMException && cause.name === 'NotAllowedError'
        ? '麦克风权限被拒绝，请在浏览器地址栏允许麦克风访问后重试'
        : '无法打开麦克风，请确认已连接 USB 麦克风且未被其他程序占用'
    state.value = 'error'
    return
  }
  startRecorder()
}

function stop(): void {
  if (recognition) {
    recognition.stop() // onend → finish(finalText)
  } else if (recorder && recorder.state !== 'inactive') {
    recorder.stop() // onstop → transcribeUpload
  } else {
    stopTracks()
    state.value = 'idle'
  }
}

function toggle(): void {
  if (state.value === 'recording') stop()
  else void start()
}

function onDeviceSelect(event: Event): void {
  const next = (event.target as HTMLSelectElement).value
  if (next === selectedDeviceId.value) return
  selectedDeviceId.value = next
  if (state.value === 'recording') stop() // 下次录音用新设备
}

onUnmounted(() => {
  if (recognition) {
    recognition.onend = null
    recognition.abort?.()
    recognition = null
  }
  if (recorder && recorder.state !== 'inactive') {
    recorder.ondataavailable = null
    recorder.onstop = null
    recorder.stop()
    recorder = null
  }
  stopTracks()
})
</script>

<template>
  <div class="voice-input">
    <div class="voice-row">
      <button
        type="button"
        class="voice-button"
        :class="state"
        :disabled="disabled"
        :aria-label="state === 'recording' ? '停止录音' : '开始语音输入'"
        @click="toggle"
      >
        <AppIcon name="mic" :size="17" />
        <span>{{ buttonLabel }}</span>
      </button>
      <select
        v-if="audioDevices.length > 1"
        class="voice-device"
        :value="selectedDeviceId"
        :disabled="disabled"
        aria-label="选择麦克风设备"
        @change="onDeviceSelect"
      >
        <option value="">默认麦克风</option>
        <option v-for="(device, index) in audioDevices" :key="device.deviceId" :value="device.deviceId">{{ deviceLabel(device, index) }}</option>
      </select>
    </div>
    <p v-if="state === 'recording' && interim" class="voice-interim">{{ interim }}</p>
    <p v-if="error" class="voice-note error">{{ error }}</p>
    <p v-else-if="state === 'transcribing'" class="voice-note"><AppIcon name="spark" :size="14" />正在转写…</p>
    <p v-else class="voice-note"><AppIcon name="mic" :size="14" />点击说话；外设麦克风可在下拉选择</p>
  </div>
</template>

<style scoped>
.voice-input { display: flex; flex-direction: column; gap: 8px; }
.voice-row { display: flex; align-items: center; gap: 8px; }
.voice-button { display: inline-flex; align-items: center; justify-content: center; gap: 6px; min-height: 32px; border: 1px solid var(--line); border-radius: 8px; padding: 0 12px; color: var(--text-soft); background: #fff; font-size: 12px; font-weight: 700; cursor: pointer; transition: border-color var(--ease), color var(--ease), background var(--ease); }
.voice-button:hover:not(:disabled) { border-color: var(--blue); color: var(--blue); }
.voice-button:disabled { opacity: 0.55; cursor: not-allowed; }
.voice-button.recording { border-color: var(--danger); color: #fff; background: var(--danger); animation: voice-pulse 0.9s ease-in-out infinite; }
.voice-button.transcribing { border-color: var(--blue); color: var(--blue); }
.voice-button.error { border-color: var(--danger); color: var(--danger); }
@keyframes voice-pulse {
  0%, 100% { box-shadow: 0 0 0 3px var(--danger); }
  50% { box-shadow: 0 0 0 7px rgba(220, 53, 69, 0.22); }
}
.voice-device { flex: 1; min-width: 0; height: 32px; border: 1px solid var(--line); border-radius: 8px; padding: 0 10px; color: var(--text); background: #fff; font-size: 12px; }
.voice-device:focus { outline: none; border-color: var(--blue); }
.voice-interim { margin: 0; color: var(--text-soft); font-size: 11px; line-height: 1.6; }
.voice-note { display: flex; align-items: center; gap: 6px; margin: 0; color: var(--muted); font-size: 11px; line-height: 1.6; }
.voice-note .app-icon { flex: none; color: var(--blue); }
.voice-note.error { color: var(--danger); }
.voice-note.error .app-icon { color: var(--danger); }
</style>
