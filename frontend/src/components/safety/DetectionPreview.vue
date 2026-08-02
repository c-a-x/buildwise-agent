<script setup lang="ts">
defineProps<{ imageUrl?: string; alt?: string }>()
</script>

<template><div class="result-visual"><img v-if="imageUrl" :src="imageUrl" :alt="alt || '现场分析图片'" /><div v-else class="result-visual-placeholder">等待图片</div></div></template>
