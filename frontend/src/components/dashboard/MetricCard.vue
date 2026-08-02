<script setup lang="ts">
import type { IconName } from '@/components/common/AppIcon.vue'
import AppIcon from '@/components/common/AppIcon.vue'

withDefaults(defineProps<{ label: string; value: string | number; icon?: IconName; tone?: 'default' | 'danger' | 'warning' | 'success' }>(), { icon: 'dashboard', tone: 'default' })
</script>

<template><article class="metric-card"><div class="metric-top"><span class="metric-icon" :class="tone"><AppIcon :name="icon" :size="18" /></span><span class="metric-delta">实时</span></div><strong>{{ value }}</strong><p>{{ label }}</p></article></template>
