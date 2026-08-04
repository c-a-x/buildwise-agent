import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { mount, flushPromises } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { reportsApi } from '@/api/reports'
import DailyReportView from '@/views/reports/DailyReportView.vue'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/project'
import type { DailyReport } from '@/types/report'

const project: Project = { id: 'PRJ-001', code: 'DEMO-001', name: '演示项目', address: '演示地址', description: '', status: 'active', manager_user_id: 'USR-001' }
const report: DailyReport = {
  id: 'RPT-001', project_id: project.id, report_date: '2026-08-03', statistics: { incident_total: 0, risk_counts: {}, high_risk_total: 0, work_order_counts: {}, new_work_orders: 0, closed_work_orders: 0, pending_review_work_orders: 0, near_deadline_work_orders: 0, top_hazards: [] }, content: '无新增隐患', generated_by: 'USR-001', is_ai_generated: false, created_at: '2026-08-03T01:00:00Z', updated_at: '2026-08-03T01:00:00Z',
}

describe('DailyReportView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const projects = useProjectStore()
    projects.projects = [project]
    vi.spyOn(reportsApi, 'generate').mockResolvedValue(report)
  })

  afterEach(() => vi.restoreAllMocks())

  it('exposes the browser print/export action after generating a report', async () => {
    const print = vi.spyOn(window, 'print').mockImplementation(() => undefined)
    const wrapper = mount(DailyReportView)
    await flushPromises()
    const button = wrapper.findAll('button').find((candidate) => candidate.text().includes('打印 / 导出 PDF'))
    expect(button).toBeDefined()
    await button!.trigger('click')
    expect(print).toHaveBeenCalledOnce()
  })
})
