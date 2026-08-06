import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'

import http from '@/api/http'
import AuditLogView from '@/views/audit/AuditLogView.vue'

const actionsPayload = {
  success: true,
  message: '',
  request_id: 'REQ-1',
  data: ['user_login', 'user_logout', 'create_project', 'confirm_work_order', 'change_work_order_status', 'attach_work_order_image'],
}

const logsPayload = {
  success: true,
  message: '',
  request_id: 'REQ-2',
  data: {
    items: [
      { id: 'AUD-1', user_id: 'USR-002', username: '演示安全员', action: 'user_login', resource_type: 'auth', resource_id: 'USR-002', detail_json: { username: 'safety' }, ip_address: '127.0.0.1', created_at: '2026-08-06T08:00:00Z' },
      { id: 'AUD-2', user_id: 'USR-001', username: '演示项目经理', action: 'create_project', resource_type: 'project', resource_id: 'PRJ-002', detail_json: { code: 'DEMO-002' }, ip_address: null, created_at: '2026-08-06T09:00:00Z' },
    ],
    total: 2,
    limit: 20,
    offset: 0,
  },
}

describe('AuditLogView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('loads audit logs and actions from the backend', async () => {
    const get = vi.spyOn(http, 'get').mockImplementation((url: string) => {
      if (url === '/audit/actions') return Promise.resolve({ data: actionsPayload } as never)
      return Promise.resolve({ data: logsPayload } as never)
    })

    const wrapper = mount(AuditLogView)
    await flushPromises()

    expect(get).toHaveBeenCalledWith('/audit/actions')
    expect(get).toHaveBeenCalledWith('/audit/logs', expect.anything())
    expect(wrapper.text()).toContain('登录')
    expect(wrapper.text()).toContain('创建项目')
    expect(wrapper.text()).toContain('演示安全员')
    expect(wrapper.text()).toContain('演示项目经理')
    expect(wrapper.text()).toContain('127.0.0.1')
    expect(wrapper.text()).toContain('共 2 条记录')
  })

  it('shows empty state when there are no audit logs', async () => {
    const get = vi.spyOn(http, 'get').mockImplementation((url: string) => {
      if (url === '/audit/actions') return Promise.resolve({ data: actionsPayload } as never)
      return Promise.resolve({ data: { success: true, message: '', request_id: 'REQ-3', data: { items: [], total: 0, limit: 20, offset: 0 } } } as never)
    })

    const wrapper = mount(AuditLogView)
    await flushPromises()

    expect(wrapper.text()).toContain('暂无审计记录')
    expect(get).toHaveBeenCalled()
  })
})
