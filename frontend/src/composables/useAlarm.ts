/** 隐患软报警状态机：去抖触发/解除 + Web Audio 蜂鸣联动。 */

import { onUnmounted, ref, watch } from 'vue'

import { ensureAlertAudio, startAlert, stopAlert } from '@/lib/alarmSound'
import type { DetectFrameHazard } from '@/types/safety'

const HIGH_RISK = new Set(['high', 'critical'])
const VIOLATIONS = new Set(['no_helmet', 'no_mask', 'no_safety_vest'])
const TRIGGER_STREAK = 2 // 连续 N 帧高危才触发，避免单帧误报
const CLEAR_STREAK = 3 // 连续 N 帧正常才解除

function isWorthy(hazard: DetectFrameHazard): boolean {
  return HIGH_RISK.has(hazard.risk_level) || VIOLATIONS.has(hazard.hazard_type)
}

export function useAlarm() {
  const alarmEnabled = ref(true)
  const muted = ref(false) // 静音只关声音，视觉告警保留
  const active = ref(false)
  const alarmHazards = ref<DetectFrameHazard[]>([])
  let highStreak = 0
  let normalStreak = 0

  function evaluate(hazards: DetectFrameHazard[]): void {
    if (!alarmEnabled.value) return
    if (hazards.some(isWorthy)) {
      highStreak += 1
      normalStreak = 0
      if (highStreak >= TRIGGER_STREAK && !active.value) {
        active.value = true
        alarmHazards.value = hazards.filter(isWorthy)
        if (!muted.value) startAlert()
      }
    } else {
      normalStreak += 1
      highStreak = 0
      if (normalStreak >= CLEAR_STREAK && active.value) {
        active.value = false
        alarmHazards.value = []
        stopAlert()
      }
    }
  }

  function reset(): void {
    active.value = false
    alarmHazards.value = []
    highStreak = 0
    normalStreak = 0
    stopAlert()
  }

  // 开关关闭立即解除并静音
  watch(alarmEnabled, (enabled) => {
    if (!enabled) reset()
  })

  // 静音切换：仅当报警中才需要启停声音
  watch(muted, (isMuted) => {
    if (!active.value) return
    if (isMuted) stopAlert()
    else {
      ensureAlertAudio()
      startAlert()
    }
  })

  onUnmounted(reset)

  return { alarmEnabled, muted, active, alarmHazards, evaluate, reset }
}
