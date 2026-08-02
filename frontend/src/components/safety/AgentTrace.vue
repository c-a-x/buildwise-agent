<script setup lang="ts">
import type { AgentTraceItem } from '@/types/safety'

defineProps<{ trace: AgentTraceItem[] }>()
</script>

<template><div class="trace-list"><div v-for="(item, index) in trace" :key="`${item.agent}-${index}`" class="trace-item" :class="item.status"><span class="trace-node">{{ index + 1 }}</span><div><strong>{{ item.agent }}</strong><small>{{ item.message }}</small></div></div></div></template>
