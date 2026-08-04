<script setup lang="ts">
// 只声明实际用到的字段：Hazard 与 DetectFrameHazard 均可传入
interface OverlayHazard {
  id: string
  hazard_name: string
  confidence: number
  bbox: number[] | null
}

const props = defineProps<{ hazards: OverlayHazard[] }>()

function boxStyle(hazard: OverlayHazard): Record<string, string> | null {
  const bbox = hazard.bbox
  if (!bbox || bbox.length < 4 || !bbox.slice(0, 4).every((value) => Number.isFinite(value))) return null
  const left = bbox[0]
  const top = bbox[1]
  const right = bbox[2]
  const bottom = bbox[3]
  if (left === undefined || top === undefined || right === undefined || bottom === undefined || right <= left || bottom <= top) return null
  return {
    left: `${left * 100}%`,
    top: `${top * 100}%`,
    width: `${(right - left) * 100}%`,
    height: `${(bottom - top) * 100}%`,
  }
}

function confidence(value: number): string {
  return `${Math.round(value * 100)}%`
}
</script>

<template>
  <template v-for="hazard in props.hazards" :key="hazard.id">
    <span v-if="boxStyle(hazard)" class="detection-box" :style="boxStyle(hazard) || undefined">
      <span class="detection-label">{{ hazard.hazard_name }} · {{ confidence(hazard.confidence) }}</span>
    </span>
  </template>
</template>
