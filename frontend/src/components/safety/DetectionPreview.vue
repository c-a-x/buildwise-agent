<script setup lang="ts">
import BoundingBoxOverlay from './BoundingBoxOverlay.vue'
import type { Hazard } from '@/types/safety'

defineProps<{ imageUrl?: string; alt?: string; hazards?: Hazard[] }>()
</script>

<template>
  <div class="result-visual">
    <div v-if="imageUrl" class="result-image-wrap">
      <img :src="imageUrl" :alt="alt || '现场分析图片'" />
      <BoundingBoxOverlay v-if="hazards?.length" :hazards="hazards" />
    </div>
    <div v-else class="result-visual-placeholder">等待图片</div>
    <slot />
  </div>
</template>
