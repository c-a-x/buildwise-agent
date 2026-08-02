<script setup lang="ts">
import type { WorkOrderEvent } from '@/types/workOrder'
import { formatDateTime } from '@/utils/date'
import { statusLabel } from '@/utils/risk'
import AppIcon from '@/components/common/AppIcon.vue'

defineProps<{ events: WorkOrderEvent[] }>()
</script>

<template><div class="trace-list"><div v-for="event in events" :key="event.id" class="trace-item"><span class="trace-node"><AppIcon name="check" :size="15" /></span><div><strong>{{ statusLabel(event.to_status || '') }}</strong><small>{{ event.note }}</small></div><span class="trace-time">{{ formatDateTime(event.created_at) }}</span></div></div></template>
