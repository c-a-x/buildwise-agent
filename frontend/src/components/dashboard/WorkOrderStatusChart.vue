<script setup lang="ts">
defineProps<{ values: Array<{ status: string; count: number }> }>()
</script>

<template><div class="legend-list"><p v-for="item in values" :key="item.status"><i class="medium" /><span>{{ item.status }}</span><b>{{ item.count }}</b></p></div></template>
