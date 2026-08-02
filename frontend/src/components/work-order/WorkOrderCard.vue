<script setup lang="ts">
import type { WorkOrder } from '@/types/workOrder'
import { riskLabel, statusLabel } from '@/utils/risk'

defineProps<{ order: WorkOrder }>()
</script>

<template><RouterLink class="card" :to="`/work-orders/${order.id}`"><span :class="`risk-badge ${order.risk_level}`">{{ riskLabel(order.risk_level) }}</span><h3 style="margin-top: 10px">{{ order.title }}</h3><p class="helper-text">{{ order.location }} · {{ statusLabel(order.status) }}</p></RouterLink></template>
