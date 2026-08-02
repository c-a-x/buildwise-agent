<script setup lang="ts">
import ModulePlaceholder from '@/components/common/ModulePlaceholder.vue'
</script>

<template><ModulePlaceholder eyebrow="QUALITY INSPECTION" title="工程质量巡检" agent="QualityAgent" icon="quality" description="面向实体质量、观感质量和验收节点的下一阶段能力。" :inputs="['质量巡检现场图片', '分部分项验收记录', '质量问题闭环记录']" :outputs="['缺陷分类与严重度', '质量整改任务', '复检提醒']" /></template>
