import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { workerCareApi } from '@/api/workerCare'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/project'
import WorkerCareView from '@/views/worker-care/WorkerCareView.vue'

const project: Project = { id: 'PRJ-001', code: 'DEMO-001', name: '演示项目', address: '演示地址', description: '', status: 'active', manager_user_id: 'USR-001' }

const inputSelector = 'input[aria-label="输入安全问题"]'

class MockSpeechRecognition {
  static instances: MockSpeechRecognition[] = []
  lang = ''
  interimResults = false
  continuous = false
  onresult: ((event: any) => void) | null = null
  onend: (() => void) | null = null
  onerror: ((event: any) => void) | null = null
  started = false

  constructor() {
    MockSpeechRecognition.instances.push(this)
  }

  start() {
    this.started = true
  }

  stop() {
    this.onend?.()
  }

  abort() {}
}

class MockMediaRecorder {
  static instances: MockMediaRecorder[] = []
  mimeType = 'audio/webm'
  state: 'inactive' | 'recording' = 'inactive'
  ondataavailable: ((event: { data: Blob }) => void) | null = null
  onstop: (() => void) | null = null

  constructor(_stream: MediaStream) {
    MockMediaRecorder.instances.push(this)
  }

  start() {
    this.state = 'recording'
  }

  stop() {
    this.state = 'inactive'
    this.onstop?.()
  }
}

const fakeStream = { getTracks: () => [{ stop: vi.fn() }] } as unknown as MediaStream

function stubAudioDevices(): void {
  Object.defineProperty(navigator, 'mediaDevices', {
    configurable: true,
    value: {
      getUserMedia: vi.fn().mockResolvedValue(fakeStream),
      enumerateDevices: vi.fn().mockResolvedValue([]),
    },
  })
}

describe('WorkerCareView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const projects = useProjectStore()
    projects.projects = [project]
    MockSpeechRecognition.instances = []
    MockMediaRecorder.instances = []
    stubAudioDevices()
  })

  afterEach(() => {
    vi.restoreAllMocks()
    vi.unstubAllGlobals()
    delete (navigator as unknown as { mediaDevices?: unknown }).mediaDevices
  })

  it('uses browser Web Speech (zh-CN) and fills input with final transcript', async () => {
    vi.stubGlobal('SpeechRecognition', MockSpeechRecognition)
    const wrapper = mount(WorkerCareView)
    await flushPromises()

    await wrapper.find('.voice-button').trigger('click')
    await flushPromises()

    const recognition = MockSpeechRecognition.instances[0]
    expect(recognition).toBeDefined()
    expect(recognition!.lang).toBe('zh-CN')
    expect(recognition!.interimResults).toBe(true)
    expect(recognition!.continuous).toBe(true)
    expect(recognition!.started).toBe(true)

    recognition!.onresult?.({ resultIndex: 0, results: [{ isFinal: true, 0: { transcript: '请戴好安全帽' } }] })

    await wrapper.find('.voice-button').trigger('click') // 停止 → onend → finish
    await flushPromises()

    const input = wrapper.find(inputSelector).element as HTMLInputElement
    expect(input.value).toBe('请戴好安全帽')
  })

  it('falls back to MediaRecorder upload and fills input with transcribed text', async () => {
    vi.spyOn(workerCareApi, 'transcribe').mockResolvedValue({ available: true, text: '请佩戴安全帽', reason: null, provider: 'fake_asr' })
    vi.stubGlobal('MediaRecorder', MockMediaRecorder)
    const wrapper = mount(WorkerCareView)
    await flushPromises()

    await wrapper.find('.voice-button').trigger('click')
    await flushPromises()

    expect(MockMediaRecorder.instances).toHaveLength(1)
    expect(MockMediaRecorder.instances[0]?.state).toBe('recording')
    expect(navigator.mediaDevices.getUserMedia).toHaveBeenCalled()

    await wrapper.find('.voice-button').trigger('click') // 停止 → onstop → transcribeUpload
    await flushPromises()

    expect(workerCareApi.transcribe).toHaveBeenCalledWith('PRJ-001', expect.any(Blob))
    const input = wrapper.find(inputSelector).element as HTMLInputElement
    expect(input.value).toBe('请佩戴安全帽')
  })

  it('shows reason when transcription is unavailable', async () => {
    vi.spyOn(workerCareApi, 'transcribe').mockResolvedValue({ available: false, text: '', reason: '语音转写未配置，请改用文本输入', provider: 'off' })
    vi.stubGlobal('MediaRecorder', MockMediaRecorder)
    const wrapper = mount(WorkerCareView)
    await flushPromises()

    await wrapper.find('.voice-button').trigger('click')
    await flushPromises()
    await wrapper.find('.voice-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('语音转写未配置')
  })
})
