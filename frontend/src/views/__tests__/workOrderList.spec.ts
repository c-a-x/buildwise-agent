import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { workOrdersApi } from '@/api/workOrders'
import WorkOrderListView from '@/views/work-orders/WorkOrderListView.vue'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/project'
import type { WorkOrder } from '@/types/workOrder'

const project: Project = { id: 'PRJ-001', code: 'DEMO-001', name: '演示项目', address: '演示地址', description: '', status: 'active', manager_user_id: 'USR-001' }

function makeOrder(id: string, assigneeName: string | null): WorkOrder {
  return {
    id,
    project_id: 'PRJ-001',
    incident_id: `INC-${id}`,
    source_task_id: `TASK-${id}`,
    title: `整改：未佩戴安全帽`,
    problem_description: '现场发现未佩戴安全帽',
    risk_level: 'high',
    location: 'B1',
    assignee_user_id: id === 'WO-001' ? 'USR-001' : 'USR-002',
    assignee_name: assigneeName,
    created_by: 'USR-002',
    deadline: '2026-08-06T00:00:00Z',
    status: 'pending',
    rectification_requirements: ['正确佩戴安全帽'],
    review_requirements: ['复查'],
    worker_message: '请正确佩戴安全帽',
    ai_generated: true,
    confirmed_by_human: true,
    closed_at: null,
    created_at: '2026-08-05T10:00:00Z',
    updated_at: '2026-08-05T10:00:00Z',
    events: [],
    file_url: null,
    annotated_url: null,
    evidence: [],
  }
}

describe('WorkOrderListView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const projects = useProjectStore()
    projects.projects = [project]
  })

  afterEach(() => vi.restoreAllMocks())

  it('shows assignee real name and falls back to id when name is missing', async () => {
    vi.spyOn(workOrdersApi, 'list').mockResolvedValue([
      makeOrder('WO-001', '演示项目经理'),
      makeOrder('WO-002', null),
    ])

    const wrapper = mount(WorkOrderListView)
    await flushPromises()

    expect(wrapper.text()).toContain('演示项目经理')
    expect(wrapper.text()).toContain('USR-002')
  })
})
