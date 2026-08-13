/** 隐患蜂鸣音（Web Audio API）。单例 AudioContext，必须在用户手势内解锁。 */

let audioContext: AudioContext | null = null
let intervalId: number | null = null

function ensureAudio(): AudioContext | null {
  if (typeof window === 'undefined') return null
  if (!audioContext) {
    const Ctor: typeof AudioContext | undefined =
      window.AudioContext ?? (window as unknown as { webkitAudioContext?: typeof AudioContext }).webkitAudioContext
    if (!Ctor) return null
    audioContext = new Ctor()
  }
  if (audioContext.state === 'suspended') void audioContext.resume().catch(() => {})
  return audioContext
}

function beepOnce(context: AudioContext): void {
  const oscillator = context.createOscillator()
  const gain = context.createGain()
  oscillator.type = 'square'
  oscillator.frequency.value = 880
  const now = context.currentTime
  gain.gain.setValueAtTime(0.18, now)
  gain.gain.exponentialRampToValueAtTime(0.001, now + 0.12)
  oscillator.connect(gain).connect(context.destination)
  oscillator.start(now)
  oscillator.stop(now + 0.13)
}

/** 在用户点击/开关等手势内调用一次，提前解锁 AudioContext。 */
export function ensureAlertAudio(): void {
  ensureAudio()
}

export function startAlert(): void {
  const context = ensureAudio()
  if (!context) return
  stopAlert()
  beepOnce(context)
  intervalId = window.setInterval(() => beepOnce(context), 600)
}

export function stopAlert(): void {
  if (intervalId !== null) {
    clearInterval(intervalId)
    intervalId = null
  }
  if (audioContext && audioContext.state !== 'suspended') void audioContext.suspend()
}

export function isAlertPlaying(): boolean {
  return intervalId !== null
}
