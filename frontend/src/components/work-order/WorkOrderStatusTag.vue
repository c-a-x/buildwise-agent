<script setup lang="ts">
import { statusLabel } from '@/utils/risk'

defineProps<{ status: string }>()
</script>

<template><span class="status-pill">{{ statusLabel(status) }}</span></template>
