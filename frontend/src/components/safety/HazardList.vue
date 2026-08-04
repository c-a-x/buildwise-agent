<script setup lang="ts">
import type { Hazard } from '@/types/safety'
import { riskLabel } from '@/utils/risk'

defineProps<{ hazards: Hazard[] }>()
</script>

<template>
  <div class="form-grid">
    <article v-for="hazard in hazards" :key="hazard.id" class="hazard-card">
      <div class="hazard-head"><strong>{{ hazard.hazard_name }}</strong><span :class="`risk-badge ${hazard.risk_level}`">{{ riskLabel(hazard.risk_level) }}</span></div>
      <p>{{ hazard.description }}</p>
      <div class="confidence">识别置信度 {{ Math.round(hazard.confidence * 100) }}%</div>
    </article>
  </div>
</template>
