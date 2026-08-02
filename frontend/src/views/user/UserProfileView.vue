<script setup lang="ts">
import { computed } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const roleLabel = computed(() => ({ admin: '系统管理员', project_manager: '项目经理', safety_officer: '安全员', quality_inspector: '质检员', worker: '工友' })[auth.user?.role || 'worker'])
</script>

<template><div><AppPageHeader eyebrow="ACCOUNT PROFILE" title="用户中心" description="查看当前账号身份、项目协作角色和离线 Provider 状态。"><template #actions><button class="secondary-button" type="button" disabled><AppIcon name="settings" :size="15" />编辑资料 · 后续版本</button></template></AppPageHeader><div class="profile-grid"><section class="card profile-card"><div class="profile-avatar">{{ auth.user?.real_name.slice(0, 1) }}</div><h2>{{ auth.user?.real_name }}</h2><p>{{ auth.user?.username }}</p><span class="status-pill success" style="margin-top: 15px">{{ roleLabel }}</span></section><section class="card"><div class="card-head"><div><p class="section-kicker">IDENTITY</p><h3>账号信息</h3></div><span>只读视图</span></div><div class="profile-details"><div class="detail-line"><span>用户编号</span><strong class="mono">{{ auth.user?.id }}</strong></div><div class="detail-line"><span>用户名</span><strong>{{ auth.user?.username }}</strong></div><div class="detail-line"><span>真实姓名</span><strong>{{ auth.user?.real_name }}</strong></div><div class="detail-line"><span>手机号</span><strong>{{ auth.user?.phone || '未填写' }}</strong></div><div class="detail-line"><span>账号状态</span><strong class="success-text">{{ auth.user?.is_active ? '正常' : '已停用' }}</strong></div><div class="detail-line"><span>AI 边界</span><strong>结果必须人工复核</strong></div></div></section></div></div></template>
