import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import ForgotPasswordView from '@/views/auth/ForgotPasswordView.vue'

describe('ForgotPasswordView', () => {
  it('explains the offline recovery path without a fake planned status', () => {
    const wrapper = mount(ForgotPasswordView, { global: { stubs: { RouterLink: true } } })

    expect(wrapper.text()).toContain('已登录用户进入用户中心修改密码')
    expect(wrapper.text()).toContain('未登录用户联系管理员')
    expect(wrapper.text()).not.toContain('规划中')
    expect(wrapper.find('[to="/login"]').exists()).toBe(true)
  })
})
