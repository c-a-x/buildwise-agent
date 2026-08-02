<script setup lang="ts">
import AppIcon from './AppIcon.vue'
import AppPageHeader from './AppPageHeader.vue'

defineProps<{
  title: string
  eyebrow: string
  agent: string
  description: string
  inputs: string[]
  outputs: string[]
  icon: 'quality' | 'leaf'
}>()
</script>

<template>
  <div>
    <AppPageHeader :eyebrow="eyebrow" :title="title" :description="description" />
    <section class="placeholder-hero card">
      <div class="placeholder-orbit"><AppIcon :name="icon" :size="30" /></div>
      <div>
        <div class="status-line"><span class="status-pill warning">规划中</span><span class="mono">{{ agent }}</span></div>
        <h2>让下一阶段能力接入真实现场数据</h2>
        <p>当前页面保留完整信息架构、模块状态接口和未来数据契约，便于后续接入模型而不改变项目协作流程。</p>
      </div>
    </section>
    <div class="placeholder-grid">
      <section class="card"><div class="card-head"><h3>计划输入</h3><span>数据准备</span></div><ul class="clean-list"><li v-for="item in inputs" :key="item"><AppIcon name="check" :size="15" />{{ item }}</li></ul></section>
      <section class="card"><div class="card-head"><h3>计划输出</h3><span>业务结果</span></div><ul class="clean-list"><li v-for="item in outputs" :key="item"><AppIcon name="spark" :size="15" />{{ item }}</li></ul></section>
    </div>
    <section class="card endpoint-card"><div class="card-head"><h3>当前状态</h3><span>接口已预留</span></div><div class="endpoint-row"><span class="status-dot online" />状态接口可查询，分析接口返回 501 占位响应</div><div class="endpoint-row"><span class="status-dot muted" />完成真实模型评估、数据治理和人工复核规则后开放</div></section>
  </div>
</template>
