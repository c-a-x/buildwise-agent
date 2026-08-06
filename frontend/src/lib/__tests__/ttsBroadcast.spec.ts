import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  isAnnounceableHazard,
  speakHazards,
  stopBroadcast,
  ttsSupported,
  unlockTts,
} from '@/lib/ttsBroadcast'

class MockUtterance {
  static instances: MockUtterance[] = []
  text: string
  lang = ''
  voice: unknown = null
  rate = 1
  pitch = 1
  volume = 1
  constructor(text: string) {
    this.text = text
    MockUtterance.instances.push(this)
  }
}

const speakMock = vi.fn()
const cancelMock = vi.fn()
const getVoicesMock = vi.fn()

function stubSynth(voices: { lang: string; localService?: boolean; name: string }[] = []): void {
  vi.stubGlobal('speechSynthesis', {
    speak: speakMock,
    cancel: cancelMock,
    getVoices: getVoicesMock.mockReturnValue(voices),
    speaking: false,
    pending: false,
  })
  vi.stubGlobal('SpeechSynthesisUtterance', MockUtterance)
}

beforeEach(() => {
  MockUtterance.instances = []
  speakMock.mockClear()
  cancelMock.mockClear()
  getVoicesMock.mockClear()
  stubSynth([
    { lang: 'zh-CN', localService: true, name: 'Microsoft Huihui' },
    { lang: 'en-US', localService: true, name: 'Microsoft David' },
  ])
})

afterEach(() => {
  vi.unstubAllGlobals()
})

describe('ttsBroadcast', () => {
  it('ttsSupported 在有 API 时为 true，缺失时为 false', () => {
    expect(ttsSupported()).toBe(true)
    vi.unstubAllGlobals()
    expect(ttsSupported()).toBe(false)
  })

  it('speakHazards 用 zh-CN 语音连接播报多个隐患名', () => {
    speakHazards(['未佩戴安全帽', '未穿反光安全背心'])
    expect(cancelMock).toHaveBeenCalledTimes(1)
    expect(speakMock).toHaveBeenCalledTimes(1)
    const utterance = MockUtterance.instances[0]!
    expect(utterance.text).toBe('未佩戴安全帽，未穿反光安全背心')
    expect(utterance.lang).toBe('zh-CN')
    expect(utterance.voice).toMatchObject({ lang: 'zh-CN', name: 'Microsoft Huihui' })
  })

  it('相同文案在去重窗口内不重复播报，不同文案正常播报', () => {
    speakHazards(['未佩戴安全帽'])
    speakHazards(['未佩戴安全帽'])
    expect(speakMock).toHaveBeenCalledTimes(1)
    speakHazards(['未穿反光安全背心'])
    expect(speakMock).toHaveBeenCalledTimes(2)
  })

  it('空数组或全空串不播报', () => {
    speakHazards([])
    speakHazards(['', '  '])
    expect(speakMock).not.toHaveBeenCalled()
  })

  it('stopBroadcast 取消当前播报', () => {
    stopBroadcast()
    expect(cancelMock).toHaveBeenCalledTimes(1)
  })

  it('unlockTts 在可播报时发送一条静音预热 utterance', () => {
    unlockTts()
    expect(speakMock).toHaveBeenCalledTimes(1)
    expect(MockUtterance.instances[0]!.volume).toBe(0)
  })

  it('isAnnounceableHazard 判定高危与违规类型', () => {
    expect(isAnnounceableHazard({ risk_level: 'high' })).toBe(true)
    expect(isAnnounceableHazard({ risk_level: 'critical' })).toBe(true)
    expect(isAnnounceableHazard({ risk_level: 'medium', hazard_type: 'no_mask' })).toBe(true)
    expect(isAnnounceableHazard({ risk_level: 'medium', hazard_type: 'other' })).toBe(false)
    expect(isAnnounceableHazard({ risk_level: 'normal' })).toBe(false)
  })
})
