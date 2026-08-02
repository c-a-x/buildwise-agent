<script setup lang="ts">
import AppState from './AppState.vue'

const props = defineProps<{ title?: string; description?: string }>()
</script>

<template><AppState type="error" :title="props.title || '加载失败'" :description="props.description"><slot /></AppState></template>
