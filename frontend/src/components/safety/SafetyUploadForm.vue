<script setup lang="ts">
import AppIcon from '@/components/common/AppIcon.vue'

defineProps<{ disabled?: boolean }>()
defineEmits<{ change: [event: Event] }>()
</script>

<template><label class="upload-zone"><input type="file" accept="image/jpeg,image/png,image/webp" :disabled="disabled" @change="$emit('change', $event)" /><span class="upload-icon"><AppIcon name="upload" :size="22" /></span><strong>选择现场图片</strong><small>JPEG / PNG / WEBP · 最大 10 MB</small></label></template>
