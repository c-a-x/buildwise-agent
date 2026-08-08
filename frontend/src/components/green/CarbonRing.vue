<script setup lang="ts">
import { computed, onBeforeUnmount, ref, watch } from 'vue'

import type { CarbonStage } from '@/types/green'

interface RingSegment extends CarbonStage {
  color: string
  start: number
  arc: number
}

const props = defineProps<{
  stages: CarbonStage[]
  total: number
  unit: string
}>()

const SEGMENT_COLORS = ['var(--primary)', 'var(--cyan)', 'var(--accent)'] as const

const progress = ref(0)
const shownTotal = ref(0)
let rafId = 0

const segments = computed<RingSegment[]>(() => {
  let start = 0
  return props.stages.slice(0, 3).map((stage, index) => {
    const arc = Math.max(stage.share * 100, 0.5)
    const segment: RingSegment = {
      ...stage,
      color: SEGMENT_COLORS[index % SEGMENT_COLORS.length] as string,
      start,
      arc,
    }
    start += stage.share * 100
    return segment
  })
})

const displayTotal = computed(() => {
  if (Number.isNaN(shownTotal.value)) return '0.00'
  return shownTotal.value.toLocaleString('zh-CN', { minimumFractionDigits: 2, maximumFractionDigits: 2 })
})

function fmt(value: number): string {
  if (value === null || value === undefined || Number.isNaN(value)) return '—'
  return value.toFixed(2)
}

function pct(share: number): string {
  return `${Math.round(share * 100)}%`
}

function animate(targetTotal: number): void {
  if (typeof cancelAnimationFrame === 'function' && rafId) cancelAnimationFrame(rafId)

  const canAnimate =
    typeof window !== 'undefined' &&
    typeof window.matchMedia === 'function' &&
    !window.matchMedia('(prefers-reduced-motion: reduce)').matches &&
    typeof requestAnimationFrame === 'function' &&
    typeof performance !== 'undefined'

  if (!canAnimate) {
    progress.value = 1
    shownTotal.value = targetTotal
    return
  }

  const from = shownTotal.value
  const startTime = performance.now()
  const duration = 900
  const easeOutCubic = (t: number): number => 1 - Math.pow(1 - t, 3)

  const step = (now: number): void => {
    const t = Math.min((now - startTime) / duration, 1)
    const eased = easeOutCubic(t)
    progress.value = eased
    shownTotal.value = from + (targetTotal - from) * eased
    if (t < 1) rafId = requestAnimationFrame(step)
  }
  rafId = requestAnimationFrame(step)
}

watch(() => props.total, (value) => animate(value), { immediate: true })

onBeforeUnmount(() => {
  if (typeof cancelAnimationFrame === 'function' && rafId) cancelAnimationFrame(rafId)
})
</script>

<template>
  <section class="ring-hero">
    <div class="ring-visual">
      <div class="ring-halo" aria-hidden="true" />
      <div class="ring">
        <svg viewBox="0 0 220 220" role="img" aria-label="碳排放分阶段占比环形图">
          <g transform="rotate(-90 110 110)">
            <circle cx="110" cy="110" r="88" fill="none" stroke="var(--surface-muted)" stroke-width="26" />
            <circle
              v-for="segment in segments"
              :key="segment.stage"
              cx="110"
              cy="110"
              r="88"
              fill="none"
              :stroke="segment.color"
              stroke-width="26"
              pathLength="100"
              stroke-linecap="round"
              :stroke-dasharray="`${segment.arc * progress} ${100 - segment.arc * progress}`"
              :stroke-dashoffset="100 - segment.start"
            />
          </g>
        </svg>
        <div class="ring-center">
          <strong>{{ displayTotal }}</strong>
          <span>{{ unit }}</span>
        </div>
      </div>
    </div>

    <div class="ring-side">
      <p class="section-kicker">CARBON BREAKDOWN</p>
      <h3>分阶段排放占比</h3>
      <ul class="ring-legend">
        <li v-for="segment in segments" :key="segment.stage">
          <span class="legend-dot" :style="{ background: segment.color }" />
          <div class="legend-meta">
            <strong>{{ segment.stage }} · {{ segment.stage_name }}</strong>
            <small>{{ segment.items_count }} 条记录</small>
          </div>
          <div class="legend-value">
            <strong>{{ fmt(segment.emission) }}</strong>
            <small>{{ pct(segment.share) }}</small>
          </div>
        </li>
      </ul>
    </div>
  </section>
</template>

<style scoped>
.ring-hero {
  display: grid;
  grid-template-columns: minmax(0, 1.1fr) minmax(280px, 0.9fr);
  align-items: center;
  gap: 30px;
  overflow: hidden;
  border: 1px solid var(--line);
  border-radius: var(--radius-md);
  padding: 26px 30px;
  background: var(--surface);
  box-shadow: var(--shadow-md);
}
.ring-visual { position: relative; display: grid; place-items: center; }
.ring { position: relative; width: 230px; height: 230px; }
.ring svg { width: 100%; height: 100%; overflow: visible; }
.ring-halo {
  position: absolute;
  inset: 16px;
  border-radius: 50%;
  border: 1px solid var(--primary-soft);
  background: transparent;
}
.ring-center {
  position: absolute;
  inset: 0;
  display: grid;
  place-content: center;
  text-align: center;
}
.ring-center strong {
  font-family: 'Fira Code', monospace;
  font-size: 34px;
  letter-spacing: -0.05em;
  line-height: 1.1;
}
.ring-center span {
  margin-top: 3px;
  color: var(--muted);
  font-family: 'Fira Code', monospace;
  font-size: 11px;
  letter-spacing: 0.04em;
}
.ring-side .section-kicker { margin-bottom: 5px; }
.ring-side h3 { margin-bottom: 2px; font-size: 15px; }
.ring-legend { display: grid; gap: 0; padding: 0; margin: 8px 0 0; list-style: none; }
.ring-legend li {
  display: grid;
  grid-template-columns: 10px minmax(0, 1fr) auto;
  align-items: center;
  gap: 11px;
  border-top: 1px solid var(--line);
  padding: 12px 0;
}
.ring-legend li:first-child { border-top: 0; padding-top: 2px; }
.legend-dot { width: 9px; height: 9px; border-radius: 50%; }
.legend-meta strong, .legend-meta small, .legend-value strong, .legend-value small { display: block; }
.legend-meta strong { font-size: 12px; }
.legend-meta small { margin-top: 3px; color: var(--muted); font-size: 10px; }
.legend-value { text-align: right; }
.legend-value strong { font-family: 'Fira Code', monospace; font-size: 13px; }
.legend-value small { margin-top: 3px; color: var(--muted); font-size: 10px; }

@keyframes halo-pulse {
  0%, 100% { opacity: 0.5; transform: scale(0.98); }
  50% { opacity: 1; transform: scale(1.04); }
}

@media (max-width: 900px) {
  .ring-hero { grid-template-columns: 1fr; justify-items: center; }
  .ring-side { width: 100%; }
}
</style>
