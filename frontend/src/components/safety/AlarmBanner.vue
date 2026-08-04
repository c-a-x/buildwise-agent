<script setup lang="ts">
/** 隐患软报警横幅：高危红色横幅 + 报警/静音/暂停开关 + 检测统计。 */

import AppIcon from '@/components/common/AppIcon.vue'
import type { DetectFrameHazard } from '@/types/safety'

defineProps<{
  active: boolean
  hazards: DetectFrameHazard[]
  alarmEnabled: boolean
  muted: boolean
  running: boolean
  analyzing: boolean
  framesAnalyzed: number
  latencyMs: number | null
  statusMessage: string
}>()

const emit = defineEmits<{
  (e: 'update:alarmEnabled', value: boolean): void
  (e: 'update:muted', value: boolean): void
  (e: 'toggle-running'): void
}>()
</script>

<template>
  <div class="alarm-banner" :class="{ active }">
    <div class="banner-left">
      <template v-if="active">
        <AppIcon name="bell" :size="18" /><strong>检测到 {{ hazards.length }} 项高风险隐患</strong>
        <span class="violation-chip" v-for="hazard in hazards" :key="hazard.id">{{ hazard.hazard_name }}</span>
      </template>
      <template v-else>
        <span class="status-dot" :class="running ? 'online' : ''" /><strong>{{ statusMessage }}</strong>
      </template>
    </div>
    <div class="banner-stats">
      <span class="mono">{{ framesAnalyzed }} 帧</span>
      <span class="mono">{{ latencyMs !== null ? `${latencyMs}ms/帧` : '--ms/帧' }}</span>
      <span class="mono">{{ analyzing ? '检测中' : '待机' }}</span>
    </div>
    <div class="banner-ctls">
      <button type="button" class="ctl-btn" :class="{ on: alarmEnabled }" @click="emit('update:alarmEnabled', !alarmEnabled)"><AppIcon name="bell" :size="14" />报警</button>
      <button type="button" class="ctl-btn" :class="{ on: !muted }" @click="emit('update:muted', !muted)"><AppIcon name="spark" :size="14" />声音</button>
      <button type="button" class="ctl-btn" :class="{ on: running }" @click="emit('toggle-running')"><AppIcon :name="running ? 'refresh' : 'arrow'" :size="14" />{{ running ? '暂停' : '继续' }}</button>
    </div>
  </div>
</template>

<style scoped>
.alarm-banner { display: flex; align-items: center; flex-wrap: wrap; gap: 12px; border: 1px solid var(--line); border-radius: 12px; padding: 10px 14px; background: #fff; transition: border-color var(--ease), background var(--ease); }
.alarm-banner.active { border-color: var(--danger); background: #fdecec; }
.banner-left { display: flex; align-items: center; flex-wrap: wrap; gap: 8px; min-width: 0; }
.banner-left .app-icon { color: var(--danger); animation: bell-ring 1s ease-in-out infinite; }
.alarm-banner.active .banner-left strong { color: var(--danger); font-size: 13px; }
.banner-left strong { font-size: 12px; color: var(--text); }
.violation-chip { border-radius: 999px; padding: 2px 9px; color: #a13237; background: #fff; border: 1px solid #f0c4c6; font-size: 10px; font-weight: 800; }
@keyframes bell-ring {
  0%, 100% { transform: rotate(0); }
  20% { transform: rotate(-14deg); }
  40% { transform: rotate(12deg); }
  60% { transform: rotate(-8deg); }
  80% { transform: rotate(6deg); }
}
.banner-stats { display: flex; align-items: center; gap: 12px; margin-left: auto; color: var(--muted); font-size: 11px; }
.banner-ctls { display: flex; align-items: center; gap: 6px; }
.ctl-btn { display: inline-flex; align-items: center; gap: 5px; min-height: 28px; border: 1px solid var(--line); border-radius: 8px; padding: 0 10px; color: var(--text-soft); background: #fff; font-size: 11px; font-weight: 800; cursor: pointer; transition: border-color var(--ease), color var(--ease), background var(--ease); }
.ctl-btn:hover { border-color: var(--blue); color: var(--blue); }
.ctl-btn.on { border-color: var(--blue); color: #fff; background: var(--blue); }
</style>
