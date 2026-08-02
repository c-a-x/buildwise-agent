<script setup lang="ts">
import AppIcon from './AppIcon.vue'

withDefaults(defineProps<{ type?: 'loading' | 'empty' | 'error'; title?: string; description?: string }>(), { type: 'empty' })
</script>

<template>
  <div class="state-card" :class="`state-${type}`" role="status">
    <div class="state-icon"><AppIcon :name="type === 'error' ? 'close' : type === 'loading' ? 'refresh' : 'info'" :size="22" /></div>
    <strong>{{ title || (type === 'loading' ? '正在加载' : type === 'error' ? '加载失败' : '暂无数据') }}</strong>
    <p>{{ description || (type === 'loading' ? '请稍候，系统正在准备内容。' : type === 'error' ? '请检查服务连接后重试。' : '完成一次安全分析后，这里会显示真实业务数据。') }}</p>
    <slot />
  </div>
</template>
