<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template><ModulePlaceholder eyebrow="GREEN CONSTRUCTION" title="绿色建造" agent="GreenAgent" icon="leaf" description="面向材料、机械能耗与施工过程的碳排估算和减排协同。" :inputs="['材料清单与用量', '机械能耗记录', '运输与周转数据']" :outputs="['阶段碳排估算', '材料对比分析', '绿色施工建议']" /></template>
