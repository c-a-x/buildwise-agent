<script setup lang="ts">
/** 实时监控：视频源 → 逐帧 YOLO 检测画框 → 高危隐患软报警。 */

import { computed, onMounted, watch } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import AlarmBanner from '@/components/safety/AlarmBanner.vue'
import RealtimeSourcePicker from '@/components/safety/RealtimeSourcePicker.vue'
import { useAlarm } from '@/composables/useAlarm'
import { useRealtimeDetection } from '@/composables/useRealtimeDetection'
import { riskLabel } from '@/utils/risk'

const detection = useRealtimeDetection()
const { analyzing, running, error, lastResult, framesAnalyzed, lastLatencyMs, start, stop } = detection
const alarm = useAlarm()
const { active: alarmActive, alarmEnabled, muted, alarmHazards, evaluate, reset } = alarm

// 模型可用才评估报警；不可用（降级为仅显示）立即解除
watch(lastResult, (result) => {
  if (!result) return
  if (result.available) evaluate(result.hazards)
  else reset()
})

const liveHazards = computed(() => lastResult.value?.hazards ?? [])
const statusMessage = computed(() => {
  if (error.value) return error.value
  if (lastResult.value?.available) return `YOLO 实时检测在线 · 已识别 ${liveHazards.value.length} 项隐患`
  if (lastResult.value) return lastResult.value.message || '实时检测模型不可用，仅显示画面不检测'
  return '正在启动实时检测…'
})
const providerLabel = computed(() => {
  const provider = lastResult.value?.provider ?? ''
  return provider.replace(/^safety_hybrid:?/, '').toUpperCase() || 'YOLO'
})

onMounted(() => start())

function toggleRunning(): void {
  if (running.value) stop()
  else start()
}

// 视频源切换后清空上一源的检测结果，避免旧检测框残留在新画面上
function onSourceChange(): void {
  detection.reset()
}
</script>

<template>
  <div>
    <AppPageHeader eyebrow="REALTIME SAFETY" title="实时监控" description="接入 ESP32-CAM / USB 摄像头 / 演示画面，逐帧进行 YOLO 隐患检测，高危违规自动触发软报警。">
      <template #actions><span class="status-pill" :class="lastResult?.available === false ? 'warning' : 'dark'"><span class="status-dot" :class="lastResult?.available === false ? '' : 'online'" />{{ providerLabel }}</span></template>
    </AppPageHeader>

    <AlarmBanner
      :active="alarmActive"
      :hazards="alarmHazards"
      :alarm-enabled="alarmEnabled"
      :muted="muted"
      :running="running"
      :analyzing="analyzing"
      :frames-analyzed="framesAnalyzed"
      :latency-ms="lastLatencyMs"
      :status-message="statusMessage"
      @update:alarm-enabled="alarmEnabled = $event"
      @update:muted="muted = $event"
      @toggle-running="toggleRunning"
    />

    <div class="realtime-layout">
      <section class="card stage-card">
        <div class="card-head">
          <div><p class="section-kicker">VIDEO FEED</p><h3>现场视频流</h3></div>
          <span class="mono">1 帧/秒 · 仅本机分析</span>
        </div>
        <RealtimeSourcePicker :frame-source="detection.frameSource" :hazards="liveHazards" :alarm-active="alarmActive" :analyzing="analyzing" :running="running" @source-change="onSourceChange" />
      </section>

      <aside class="card side-panel">
        <div class="card-head"><div><p class="section-kicker">LIVE HAZARDS</p><h3>实时隐患</h3></div><span class="mono">{{ liveHazards.length }} 项</span></div>
        <AppState v-if="!lastResult && !analyzing" title="等待首帧检测" description="实时检测启动后，每一帧识别到的隐患会实时列出。" />
        <div v-else-if="liveHazards.length" class="live-list">
          <article v-for="hazard in liveHazards" :key="hazard.id" class="live-item" :class="{ 'is-alarm': alarmHazards.some((h) => h.id === hazard.id) }">
            <span :class="`risk-badge ${hazard.risk_level}`"><i class="risk-dot" />{{ riskLabel(hazard.risk_level) }}</span>
            <strong>{{ hazard.hazard_name }}</strong>
            <small>置信度 {{ Math.round(hazard.confidence * 100) }}%</small>
          </article>
        </div>
        <AppState v-else title="当前画面未发现隐患" description="检测正常，等待违规行为出现。" />

        <div class="side-note">
          <AppIcon name="info" :size="15" />
          <span><b>软报警触发规则：</b>连续 2 帧出现高危（高风险/重大风险）或未戴安全帽、未戴口罩、未穿反光衣违规即报警；连续 3 帧正常自动解除。</span>
        </div>
      </aside>
    </div>
  </div>
</template>

<style scoped>
.realtime-layout { display: grid; grid-template-columns: minmax(0, 1fr) 320px; gap: 18px; align-items: start; margin-top: 18px; }
@media (max-width: 1080px) { .realtime-layout { grid-template-columns: 1fr; } }
.stage-card { min-width: 0; }
.side-panel { display: flex; flex-direction: column; gap: 12px; }
.live-list { display: flex; flex-direction: column; gap: 8px; max-height: 380px; overflow-y: auto; }
.live-item { display: grid; grid-template-columns: auto 1fr; gap: 4px 10px; align-items: center; border: 1px solid var(--line); border-radius: 9px; padding: 9px 11px; background: #fff; }
.live-item.is-alarm { border-color: var(--danger); box-shadow: 0 0 0 1px var(--danger); background: #fff7f7; }
.live-item strong { font-size: 12px; color: var(--text); }
.live-item small { grid-column: 2; color: var(--muted); font-size: 10px; }
.side-note { display: flex; align-items: flex-start; gap: 8px; border: 1px dashed var(--line); border-radius: 9px; padding: 10px 11px; color: var(--muted); font-size: 11px; line-height: 1.6; }
.side-note .app-icon { flex: none; margin-top: 1px; color: var(--blue); }
.side-note b { color: var(--text-soft); font-weight: 800; }
</style>
