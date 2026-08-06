import { beforeEach, describe, expect, it, vi } from 'vitest'
import { nextTick } from 'vue'

const mocks = vi.hoisted(() => ({
  speakHazards: vi.fn(),
  stopBroadcast: vi.fn(),
}))

vi.mock('@/lib/alarmSound', () => ({
  ensureAlertAudio: vi.fn(),
  startAlert: vi.fn(),
  stopAlert: vi.fn(),
}))

vi.mock('@/lib/ttsBroadcast', async (importOriginal) => {
  const actual = await importOriginal<typeof import('@/lib/ttsBroadcast')>()
  return { ...actual, speakHazards: mocks.speakHazards, stopBroadcast: mocks.stopBroadcast }
})

import { useAlarm } from '@/composables/useAlarm'
import type { DetectFrameHazard } from '@/types/safety'

function hazard(overrides: Partial<DetectFrameHazard> = {}): DetectFrameHazard {
  return {
    id: 'hz-1',
    hazard_type: 'no_helmet',
    hazard_name: '未佩戴安全帽',
    description: '',
    confidence: 0.9,
    risk_level: 'high',
    bbox: null,
    ...overrides,
  }
}

beforeEach(() => {
  mocks.speakHazards.mockClear()
  mocks.stopBroadcast.mockClear()
})

describe('useAlarm', () => {
  it('连续 2 帧高危触发报警并语音播报隐患名', () => {
    const alarm = useAlarm()
    alarm.evaluate([hazard()])
    alarm.evaluate([hazard()])
    expect(alarm.active.value).toBe(true)
    expect(mocks.speakHazards).toHaveBeenCalledTimes(1)
    expect(mocks.speakHazards).toHaveBeenCalledWith(['未佩戴安全帽'])
  })

  it('静音时不语音播报，仅保留视觉告警', () => {
    const alarm = useAlarm()
    alarm.muted.value = true
    alarm.evaluate([hazard()])
    alarm.evaluate([hazard()])
    expect(alarm.active.value).toBe(true)
    expect(mocks.speakHazards).not.toHaveBeenCalled()
  })

  it('连续 3 帧正常解除报警并停止播报', () => {
    const alarm = useAlarm()
    alarm.evaluate([hazard()])
    alarm.evaluate([hazard()])
    alarm.evaluate([])
    alarm.evaluate([])
    alarm.evaluate([])
    expect(alarm.active.value).toBe(false)
    expect(mocks.stopBroadcast).toHaveBeenCalled()
  })

  it('报警中解除静音会重新播报当前隐患', async () => {
    const alarm = useAlarm()
    alarm.evaluate([hazard()])
    alarm.evaluate([hazard()])
    mocks.speakHazards.mockClear()
    alarm.muted.value = true
    await nextTick()
    alarm.muted.value = false
    await nextTick()
    expect(mocks.speakHazards).toHaveBeenCalledWith(['未佩戴安全帽'])
  })
})
