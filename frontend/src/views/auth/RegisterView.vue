<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRouter } from 'vue-router'

import { getApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'
import type { RegisterPayload } from '@/types/auth'
import { validatePassword, validateUsername } from '@/utils/validation'

const auth = useAuthStore()
const router = useRouter()
const form = reactive<RegisterPayload>({ username: '', real_name: '', password: '', password_confirm: '', role: 'safety_officer', phone: '' })
const errorMessage = ref('')
const fieldError = ref('')

async function submit(): Promise<void> {
  fieldError.value = validateUsername(form.username) || validatePassword(form.password) || (form.password !== form.password_confirm ? '两次输入的密码不一致' : '')
  if (fieldError.value) return
  errorMessage.value = ''
  try {
    await auth.register(form)
    await router.push({ name: 'login', query: { registered: '1' } })
  } catch (cause) {
    errorMessage.value = getApiError(cause)
  }
}
</script>

<template>
  <section class="auth-panel">
    <p class="eyebrow">CREATE ACCOUNT</p><h1>创建项目账号</h1><p class="intro">选择你的项目角色。管理员账号由系统种子或后台创建，注册页不开放管理员选项。</p>
    <div v-if="errorMessage" class="alert alert-error" role="alert">{{ errorMessage }}</div><div v-if="fieldError" class="alert alert-error" role="alert">{{ fieldError }}</div>
    <form class="auth-form" @submit.prevent="submit">
      <div class="two-fields"><div class="form-field"><label for="register-username">用户名</label><input id="register-username" v-model.trim="form.username" autocomplete="username" placeholder="3–32 位" required /></div><div class="form-field"><label for="real-name">姓名</label><input id="real-name" v-model.trim="form.real_name" autocomplete="name" placeholder="真实姓名" required /></div></div>
      <div class="form-field"><label for="register-role">项目角色</label><select id="register-role" v-model="form.role"><option value="project_manager">项目经理</option><option value="safety_officer">安全员</option><option value="quality_inspector">质检员</option><option value="worker">工友</option></select></div>
      <div class="two-fields"><div class="form-field"><label for="register-password">密码</label><input id="register-password" v-model="form.password" type="password" autocomplete="new-password" placeholder="至少 8 位" required /></div><div class="form-field"><label for="register-password-confirm">确认密码</label><input id="register-password-confirm" v-model="form.password_confirm" type="password" autocomplete="new-password" placeholder="再次输入" required /></div></div>
      <div class="form-field"><label for="phone">手机号 <span>可选</span></label><input id="phone" v-model.trim="form.phone" type="tel" autocomplete="tel" placeholder="用于后续通知接入" /></div>
      <button class="primary-button button-block" type="submit" :disabled="auth.loading">{{ auth.loading ? '正在创建…' : '创建账号' }}</button>
    </form>
    <div class="auth-links"><RouterLink to="/login">返回登录</RouterLink><span>注册即表示接受项目协作规范</span></div>
  </section>
</template>
