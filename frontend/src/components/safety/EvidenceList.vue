<script setup lang="ts">
import type { Evidence } from '@/types/safety'

defineProps<{ evidence: Evidence[] }>()
</script>

<template><div class="evidence-list"><article v-for="item in evidence" :key="item.id || item.article" class="evidence-item"><strong>{{ item.source }}</strong><small>{{ item.article }}</small><p>{{ item.content }}</p></article></div></template>
