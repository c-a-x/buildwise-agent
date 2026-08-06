/** 隐患语音播报（浏览器 Web Speech API）。离线可用，跟随现有报警音逻辑。 */

export const HIGH_RISK = new Set(['high', 'critical'])
export const VIOLATIONS = new Set(['no_helmet', 'no_mask', 'no_safety_vest'])
export const MIN_REPEAT_GAP_MS = 1500 // 相同文案 1.5s 内不重复播报，避免多路触发叠声

let lastText = ''
let lastSpokenAt = 0

/** 浏览器是否支持语音合成。 */
export function ttsSupported(): boolean {
  return typeof window !== 'undefined' && 'speechSynthesis' in window && 'SpeechSynthesisUtterance' in window
}

/** 与实时报警同语义：高危风险或未戴安全帽/口罩/反光衣违规。 */
export function isAnnounceableHazard(h: { risk_level: string; hazard_type?: string }): boolean {
  return HIGH_RISK.has(h.risk_level) || VIOLATIONS.has(h.hazard_type ?? '')
}

function pickZhVoice(voices: SpeechSynthesisVoice[]): SpeechSynthesisVoice | null {
  const zh = voices.filter((voice) => voice.lang.toLowerCase().startsWith('zh'))
  return zh.find((voice) => voice.localService) ?? zh[0] ?? null
}

/** 在用户点击/开关等手势内调用一次，预热语音合成，规避浏览器自动播放限制。 */
export function unlockTts(): void {
  if (!ttsSupported()) return
  const synth = window.speechSynthesis
  if (synth.speaking || synth.pending) return
  try {
    const utterance = new SpeechSynthesisUtterance(' ')
    utterance.volume = 0
    synth.speak(utterance)
  } catch {
    /* 预热失败不影响后续播报 */
  }
}

/** 播报隐患名：多隐患用中文逗号连接成一句，取 zh 语音。 */
export function speakHazards(names: string[]): void {
  if (!ttsSupported()) return
  const clean = names.map((name) => name?.trim()).filter(Boolean)
  if (!clean.length) return
  const text = clean.join('，')
  const now = Date.now()
  if (text === lastText && now - lastSpokenAt < MIN_REPEAT_GAP_MS) return
  lastText = text
  lastSpokenAt = now

  const synth = window.speechSynthesis
  synth.cancel() // 新播报打断上一次，避免叠声
  const utterance = new SpeechSynthesisUtterance(text)
  utterance.lang = 'zh-CN'
  utterance.rate = 1
  utterance.pitch = 1
  const voice = pickZhVoice(synth.getVoices())
  if (voice) utterance.voice = voice
  synth.speak(utterance)
}

/** 停止当前播报。 */
export function stopBroadcast(): void {
  if (!ttsSupported()) return
  window.speechSynthesis.cancel()
}
