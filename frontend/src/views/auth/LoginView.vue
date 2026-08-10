<script setup lang="ts">
import { reactive, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import AppIcon from '@/components/common/AppIcon.vue'
import { getApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const router = useRouter()
const route = useRoute()
const form = reactive({ username: '', password: '', remember: true })
const showPassword = ref(false)
const errorMessage = ref('')
const demoAccounts = [
  { username: 'manager', label: '项目经理' },
  { username: 'safety', label: '安全员' },
  { username: 'quality', label: '质检员' },
  { username: 'worker', label: '工友' },
]

function useDemo(username: string): void {
  form.username = username
  form.password = 'BuildWise123!'
}

function defaultRouteForRole(role: string | undefined): string {
  if (role === 'worker') return '/worker-care'
  if (role === 'quality_inspector') return '/quality'
  if (role === 'safety_officer') return '/safety/analyze'
  return '/dashboard'
}

async function submit(): Promise<void> {
  errorMessage.value = ''
  try {
    await auth.login(form)
    const redirect = typeof route.query.redirect === 'string' ? route.query.redirect : defaultRouteForRole(auth.user?.role)
    await router.push(redirect)
  } catch (cause) {
    errorMessage.value = getApiError(cause)
  }
}
</script>

<template>
  <section class="auth-panel">
    <p class="eyebrow">WELCOME BACK</p>
    <h1>登录工作空间</h1>
    <p class="intro">进入项目现场数据与 AI 协同工作台，继续处理今天的安全任务。</p>
    <div v-if="errorMessage" class="alert alert-error" role="alert">{{ errorMessage }}</div>
    <form class="auth-form" @submit.prevent="submit">
      <div class="form-field"><label for="username">用户名</label><input id="username" v-model.trim="form.username" autocomplete="username" placeholder="输入演示账号或用户名" required /></div>
      <div class="form-field"><label for="password">密码</label><div class="password-wrap"><input id="password" v-model="form.password" :type="showPassword ? 'text' : 'password'" autocomplete="current-password" placeholder="输入密码" required /><button class="password-toggle" type="button" :aria-label="showPassword ? '隐藏密码' : '显示密码'" @click="showPassword = !showPassword"><AppIcon :name="showPassword ? 'close' : 'lock'" :size="16" /></button></div></div>
      <label class="checkbox-line"><input v-model="form.remember" type="checkbox" />记住本次登录</label>
      <button class="primary-button button-block" type="submit" :disabled="auth.loading"><AppIcon v-if="!auth.loading" name="arrow" :size="16" />{{ auth.loading ? '正在登录…' : '登录工作台' }}</button>
    </form>
    <div class="auth-links"><RouterLink to="/register">还没有账号？创建账号</RouterLink><RouterLink to="/forgot-password">忘记密码</RouterLink></div>
    <div class="demo-box"><div class="demo-box-head"><strong>演示账号</strong><span>密码统一为 BuildWise123!</span></div><div class="demo-accounts"><button v-for="account in demoAccounts" :key="account.username" class="demo-account" type="button" @click="useDemo(account.username)"><AppIcon name="user" :size="13" />{{ account.label }}</button></div></div>
  </section>
</template>
