import { describe, expect, it } from 'vitest'
import { mount } from '@vue/test-utils'

import GreenConstructionView from '@/views/green/GreenConstructionView.vue'

describe('planned module pages', () => {
  it('shows the green construction agent, status, inputs, and outputs', () => {
    const wrapper = mount(GreenConstructionView)
    expect(wrapper.text()).toContain('GreenAgent')
    expect(wrapper.text()).toContain('规划中')
    expect(wrapper.text()).toContain('材料清单与用量')
    expect(wrapper.text()).toContain('阶段碳排估算')
  })
})
