<script setup lang="ts">
defineProps<{ values: Array<{ date: string; count: number }> }>()
</script>

<template><div class="line-chart" role="img" aria-label="风险趋势图"><span class="helper-text">{{ values.length ? `最近 ${values.length} 天，共 ${values.reduce((total, item) => total + item.count, 0)} 项` : '暂无趋势数据' }}</span></div></template>
