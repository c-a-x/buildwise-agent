/** 隐患软报警状态机：去抖触发/解除 + Web Audio 蜂鸣 + 语音播报联动。 */

import { onUnmounted, ref, watch } from 'vue'

import { ensureAlertAudio, startAlert, stopAlert } from '@/lib/alarmSound'
import { isAnnounceableHazard, speakHazards, stopBroadcast, unlockTts } from '@/lib/ttsBroadcast'
import type { DetectFrameHazard } from '@/types/safety'

const TRIGGER_STREAK = 2 // 连续 N 帧高危才触发，避免单帧误报
const CLEAR_STREAK = 3 // 连续 N 帧正常才解除

export function useAlarm() {
  const alarmEnabled = ref(true)
  const muted = ref(false) // 静音只关声音，视觉告警保留
  const active = ref(false)
  const alarmHazards = ref<DetectFrameHazard[]>([])
  let highStreak = 0
  let normalStreak = 0
  let lastSignature = '' // 最近一次播报的隐患签名，用于场景变化时重新播报

  /** 可播报隐患的唯一名集合（排序后拼接），判断当前帧与上次播报内容是否一致。 */
  function signatureOf(hazards: DetectFrameHazard[]): string {
    const names = hazards
      .filter(isAnnounceableHazard)
      .map((hazard) => hazard.hazard_name?.trim() ?? '')
      .filter(Boolean)
    return [...new Set(names)].sort().join('|')
  }

  function evaluate(hazards: DetectFrameHazard[]): void {
    if (!alarmEnabled.value) return
    if (hazards.some(isAnnounceableHazard)) {
      highStreak += 1
      normalStreak = 0
      const signature = signatureOf(hazards)
      const isNewTrigger = !active.value
      const isChanged = active.value && signature && signature !== lastSignature
      if (highStreak >= TRIGGER_STREAK && (isNewTrigger || isChanged)) {
        active.value = true
        alarmHazards.value = hazards.filter(isAnnounceableHazard)
        lastSignature = signature
        if (!muted.value) {
          startAlert()
          speakHazards(alarmHazards.value.map((hazard) => hazard.hazard_name))
        }
      }
    } else {
      normalStreak += 1
      highStreak = 0
      if (normalStreak >= CLEAR_STREAK && active.value) {
        active.value = false
        alarmHazards.value = []
        lastSignature = ''
        stopAlert()
        stopBroadcast()
      }
    }
  }

  function reset(): void {
    active.value = false
    alarmHazards.value = []
    highStreak = 0
    normalStreak = 0
    lastSignature = ''
    stopAlert()
    stopBroadcast()
  }

  // 开关关闭立即解除并静音
  watch(alarmEnabled, (enabled) => {
    if (!enabled) reset()
  })

  // 静音切换：仅当报警中才需要启停声音/语音
  watch(muted, (isMuted) => {
    if (!active.value) return
    if (isMuted) {
      stopAlert()
      stopBroadcast()
    } else {
      ensureAlertAudio()
      unlockTts()
      startAlert()
      speakHazards(alarmHazards.value.map((hazard) => hazard.hazard_name))
    }
  })

  onUnmounted(reset)

  return { alarmEnabled, muted, active, alarmHazards, evaluate, reset }
}
