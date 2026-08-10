<script setup lang="ts">
import { computed, reactive, ref, watch } from 'vue'

import AppPageHeader from '@/components/common/AppPageHeader.vue'
import { getApiError } from '@/api/http'
import { useAuthStore } from '@/stores/auth'

const auth = useAuthStore()
const roleLabel = computed(() => ({ admin: '系统管理员', project_manager: '项目经理', safety_officer: '安全员', quality_inspector: '质检员', worker: '工友' })[auth.user?.role || 'worker'])
const profileForm = reactive({ real_name: auth.user?.real_name || '', phone: auth.user?.phone || '' })
const passwordForm = reactive({ current_password: '', new_password: '', new_password_confirm: '' })
const profileError = ref('')
const profileSuccess = ref('')
const passwordError = ref('')
const passwordSuccess = ref('')

watch(() => auth.user, (user) => {
  if (!user) return
  profileForm.real_name = user.real_name
  profileForm.phone = user.phone || ''
})

async function submitProfile(): Promise<void> {
  profileError.value = ''
  profileSuccess.value = ''
  if (!profileForm.real_name.trim()) {
    profileError.value = '请填写真实姓名'
    return
  }
  try {
    await auth.updateProfile({ real_name: profileForm.real_name.trim(), phone: profileForm.phone.trim() || null })
    profileSuccess.value = '资料已更新'
  } catch (cause) {
    profileError.value = getApiError(cause)
  }
}

async function submitPassword(): Promise<void> {
  passwordError.value = ''
  passwordSuccess.value = ''
  if (passwordForm.new_password.length < 8) {
    passwordError.value = '新密码至少需要 8 位'
    return
  }
  if (passwordForm.new_password !== passwordForm.new_password_confirm) {
    passwordError.value = '两次输入的新密码不一致'
    return
  }
  try {
    const payload = {
      current_password: passwordForm.current_password,
      new_password: passwordForm.new_password,
      new_password_confirm: passwordForm.new_password_confirm,
    }
    await auth.changePassword(payload)
    passwordForm.current_password = ''
    passwordForm.new_password = ''
    passwordForm.new_password_confirm = ''
    passwordSuccess.value = '密码已更新'
  } catch (cause) {
    passwordError.value = getApiError(cause)
  }
}
</script>

<template>
  <div>
    <AppPageHeader eyebrow="ACCOUNT PROFILE" title="用户中心" description="维护个人资料与登录凭据，用户名、角色和账号状态由系统权限控制。" />

    <div class="profile-grid">
      <section class="card profile-card">
        <div class="profile-avatar">{{ auth.user?.real_name.slice(0, 1) }}</div>
        <h2>{{ auth.user?.real_name }}</h2>
        <p>当前工作空间成员</p>
      </section>

      <section class="card">
        <div class="card-head"><div><p class="section-kicker">PROFILE</p><h3>个人资料</h3></div><span>可编辑字段</span></div>
        <form class="form-grid" data-test="profile-form" @submit.prevent="submitProfile">
          <div class="two-fields">
            <div class="form-field"><label for="profile-real-name">真实姓名 <span>*</span></label><input id="profile-real-name" v-model="profileForm.real_name" data-test="profile-real-name" autocomplete="name" required /></div>
            <div class="form-field"><label for="profile-phone">手机号</label><input id="profile-phone" v-model="profileForm.phone" data-test="profile-phone" autocomplete="tel" inputmode="tel" placeholder="未填写" /></div>
          </div>
          <p v-if="profileError" class="error-text" role="alert">{{ profileError }}</p>
          <p v-if="profileSuccess" class="success-text" role="status">{{ profileSuccess }}</p>
          <button class="primary-button" type="submit" :disabled="auth.loading">{{ auth.loading ? '保存中…' : '保存资料' }}</button>
        </form>
      </section>

      <section class="card">
        <div class="card-head"><div><p class="section-kicker">ACCESS CONTROL</p><h3>账号信息</h3></div><span>只读</span></div>
        <div class="profile-details">
          <div class="detail-line"><span>用户名</span><input class="readonly-field" data-test="profile-username" :value="auth.user?.username" readonly /></div>
          <div class="detail-line"><span>角色</span><input class="readonly-field" data-test="profile-role" :value="roleLabel" readonly /></div>
          <div class="detail-line"><span>账号状态</span><input class="readonly-field success-text" data-test="profile-status" :value="auth.user?.is_active ? '正常' : '已停用'" readonly /></div>
          <div class="detail-line"><span>AI 边界</span><strong>结果必须人工复核</strong></div>
        </div>
      </section>

      <section class="card">
        <div class="card-head"><div><p class="section-kicker">SECURITY</p><h3>修改密码</h3></div><span>离线安全流程</span></div>
        <form class="form-grid" data-test="password-form" @submit.prevent="submitPassword">
          <div class="form-field"><label for="current-password">当前密码 <span>*</span></label><input id="current-password" v-model="passwordForm.current_password" data-test="current-password" type="password" autocomplete="current-password" required /></div>
          <div class="two-fields">
            <div class="form-field"><label for="new-password">新密码 <span>*</span></label><input id="new-password" v-model="passwordForm.new_password" data-test="new-password" type="password" minlength="8" autocomplete="new-password" required /></div>
            <div class="form-field"><label for="new-password-confirm">确认新密码 <span>*</span></label><input id="new-password-confirm" v-model="passwordForm.new_password_confirm" data-test="new-password-confirm" type="password" minlength="8" autocomplete="new-password" required /></div>
          </div>
          <p class="helper-text">密码至少 8 位。修改后请使用新密码重新登录其他设备。</p>
          <p v-if="passwordError" class="error-text" role="alert">{{ passwordError }}</p>
          <p v-if="passwordSuccess" class="success-text" role="status">{{ passwordSuccess }}</p>
          <button class="primary-button" type="submit" :disabled="auth.loading">{{ auth.loading ? '更新中…' : '更新密码' }}</button>
        </form>
      </section>
    </div>
  </div>
</template>
