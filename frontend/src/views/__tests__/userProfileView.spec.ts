import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import UserProfileView from '@/views/user/UserProfileView.vue'

const user = {
  id: 'USR-002',
  username: 'safety',
  real_name: '演示安全员',
  role: 'safety_officer' as const,
  phone: null,
  is_active: true,
}

describe('UserProfileView', () => {
  afterEach(() => vi.restoreAllMocks())

  function mountView() {
    setActivePinia(createPinia())
    const auth = useAuthStore()
    auth.user = { ...user }
    return { auth, wrapper: mount(UserProfileView, { global: { stubs: { RouterLink: true } } }) }
  }

  it('edits profile fields while keeping identity fields read-only', async () => {
    const updated = { ...user, real_name: '新的安全员', phone: '13800000000' }
    vi.spyOn(authApi, 'updateProfile').mockResolvedValue(updated)
    const { wrapper } = mountView()

    expect(wrapper.find('[data-test="profile-username"]').attributes('readonly')).toBeDefined()
    expect(wrapper.find('[data-test="profile-role"]').attributes('readonly')).toBeDefined()
    await wrapper.find('[data-test="profile-real-name"]').setValue('新的安全员')
    await wrapper.find('[data-test="profile-phone"]').setValue('13800000000')
    await wrapper.find('[data-test="profile-form"]').trigger('submit')
    await flushPromises()

    expect(authApi.updateProfile).toHaveBeenCalledWith({ real_name: '新的安全员', phone: '13800000000' })
    expect(wrapper.text()).toContain('资料已更新')
    expect(wrapper.find('[data-test="profile-username"]').element).toHaveProperty('value', 'safety')
  })

  it('changes password and shows the confirmed success state', async () => {
    vi.spyOn(authApi, 'changePassword').mockResolvedValue({ changed: true })
    const { wrapper } = mountView()

    await wrapper.find('[data-test="current-password"]').setValue('BuildWise123!')
    await wrapper.find('[data-test="new-password"]').setValue('NewBuildWise123!')
    await wrapper.find('[data-test="new-password-confirm"]').setValue('NewBuildWise123!')
    await wrapper.find('[data-test="password-form"]').trigger('submit')
    await flushPromises()

    expect(authApi.changePassword).toHaveBeenCalledWith({ current_password: 'BuildWise123!', new_password: 'NewBuildWise123!', new_password_confirm: 'NewBuildWise123!' })
    expect(wrapper.text()).toContain('密码已更新')
  })

  it('does not overwrite an unsaved profile draft when the same user object changes', async () => {
    const { auth, wrapper } = mountView()
    await wrapper.find('[data-test="profile-real-name"]').setValue('未提交的姓名')

    if (!auth.user) throw new Error('test user was not initialized')
    auth.user.real_name = '后台刷新姓名'
    await flushPromises()

    expect(wrapper.find('[data-test="profile-real-name"]').element).toHaveProperty('value', '未提交的姓名')
  })
})
