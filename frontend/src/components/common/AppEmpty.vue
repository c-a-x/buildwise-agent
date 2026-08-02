<script setup lang="ts">
import AppState from './AppState.vue'

const props = defineProps<{ title?: string; description?: string }>()
</script>

<template><AppState :title="props.title || '暂无数据'" :description="props.description"><slot /></AppState></template>
