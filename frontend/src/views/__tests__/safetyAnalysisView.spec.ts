import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createMemoryHistory, createRouter } from 'vue-router'
import { mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { workOrdersApi } from '@/api/workOrders'
import SafetyAnalysisView from '@/views/safety/SafetyAnalysisView.vue'
import { useProjectStore } from '@/stores/project'
import { useSafetyStore } from '@/stores/safety'
import type { SafetyAnalysisResult } from '@/types/safety'
import type { Project } from '@/types/project'
import type { WorkOrder } from '@/types/workOrder'

const project: Project = {
  id: 'PRJ-001',
  code: 'DEMO-001',
  name: '演示项目',
  address: '演示地址',
  description: '',
  status: 'active',
  manager_user_id: 'USR-001',
}

const result: SafetyAnalysisResult = {
  task_id: 'TASK-001',
  project_id: project.id,
  upload_id: 'UPL-001',
  file_url: '/storage/uploads/site.jpg',
  annotated_url: null,
  location: 'B1',
  work_type: '主体结构',
  risk_level: 'high',
  hazards: [{ id: 'INC-001', hazard_type: 'no_helmet', hazard_name: '未佩戴安全帽', description: '请整改', confidence: 0.96, risk_level: 'high', bbox: [0.1, 0.1, 0.4, 0.4], review_required: true }],
  evidence: [],
  work_order_draft: {
    task_id: 'TASK-001', incident_id: 'INC-001', title: '整改：未佩戴安全帽', problem_description: '请整改', risk_level: 'high', location: 'B1', deadline: '2026-08-03T12:00:00Z', assignee_role: '安全员', rectification_requirements: ['佩戴安全帽'], review_requirements: ['复查'], worker_message: '请注意安全', ai_generated: true, confirmed_by_human: false, review_required: true, is_simulated: true,
  },
  worker_message: '请注意安全',
  report_preview: '发现一项隐患',
  agent_trace: [],
  review_required: true,
  is_simulated: true,
  provider_info: {},
}

describe('SafetyAnalysisView', () => {
  let router: ReturnType<typeof createRouter>

  beforeEach(async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    router = createRouter({ history: createMemoryHistory(), routes: [{ path: '/safety/analyze', component: SafetyAnalysisView }] })
    await router.push('/safety/analyze')
    await router.isReady()
    const projects = useProjectStore()
    projects.projects = [project]
    const safety = useSafetyStore()
    safety.currentResult = result
    safety.analyzing = false
    safety.loadingTask = false
    safety.error = ''
    vi.spyOn(workOrdersApi, 'create').mockResolvedValue({ id: 'WO-001' } as WorkOrder)
  })

  afterEach(() => {
    vi.restoreAllMocks()
  })

  it('disables the confirmation action after creating the formal work order', async () => {
    const wrapper = mount(SafetyAnalysisView, { global: { plugins: [router] } })
    const button = wrapper.findAll('button').find((candidate) => candidate.text().includes('确认创建正式工单'))
    expect(button).toBeDefined()
    await button!.trigger('click')
    await new Promise((resolve) => setTimeout(resolve, 0))
    const confirmed = wrapper.findAll('button').find((candidate) => candidate.text().includes('已创建工单'))
    expect(confirmed?.attributes('disabled')).toBeDefined()
  })
})
