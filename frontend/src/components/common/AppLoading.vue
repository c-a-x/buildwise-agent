<script setup lang="ts">
import AppState from './AppState.vue'

const props = defineProps<{ title?: string; description?: string }>()
</script>

<template><AppState type="loading" :title="props.title || '正在加载'" :description="props.description"><slot /></AppState></template>
