import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import http from '@/api/http'
import SystemSettingsView from '@/views/system/SystemSettingsView.vue'

describe('SystemSettingsView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('loads runtime and database status from the backend', async () => {
    const get = vi.spyOn(http, 'get').mockResolvedValue({
      data: {
        data: {
          app: 'BuildWise AI Agent',
          environment: 'development',
          providers: { vision: 'mock', retrieval: 'local_keyword', text: 'template' },
          database: { status: 'connected', dialect: 'sqlite', persistent: true },
        },
      },
    } as never)

    const wrapper = mount(SystemSettingsView)
    await flushPromises()

    expect(get).toHaveBeenCalledWith('/health')
    expect(wrapper.text()).toContain('SQLite · 已连接')
    expect(wrapper.text()).toContain('mock')
    expect(wrapper.text()).toContain('local_keyword')
    expect(wrapper.text()).toContain('template')
  })
})
