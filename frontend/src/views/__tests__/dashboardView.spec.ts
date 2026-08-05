import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { dashboardApi, type DashboardSummary } from '@/api/dashboard'
import { statsApi, type AnomalyResult } from '@/api/stats'
import DashboardView from '@/views/dashboard/DashboardView.vue'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/project'

const project: Project = { id: 'PRJ-001', code: 'DEMO-001', name: '演示项目', address: '演示地址', description: '', status: 'active', manager_user_id: 'USR-001' }
const summary: DashboardSummary = {
  metrics: { today_incidents: 0, high_risk_incidents: 0, pending_work_orders: 0, pending_review_work_orders: 0, weekly_close_rate: 0, project_members: 0 },
  risk_distribution: [],
  work_order_distribution: [],
  risk_trend: [],
  recent_tasks: [],
  due_work_orders: [],
}

function buildAnomalyResult(): AnomalyResult {
  const normalDays = Array.from({ length: 29 }, (_, index) => {
    const day = index + 7
    return { date: `2026-07-${day < 10 ? `0${day}` : day}`, count: 0, z: -0.18, anomaly: false }
  })
  return {
    available: true,
    reason: '',
    project_id: 'PRJ-001',
    module: 'safety',
    days: 30,
    z_threshold: 2.5,
    total_days: 30,
    mean: 0.3333,
    std: 1.8257,
    anomaly_days: 1,
    ratio: 0.033,
    samples: [...normalDays, { date: '2026-08-05', count: 10, z: 5.294, anomaly: true }],
  }
}

describe('DashboardView', () => {
  beforeEach(() => {
    setActivePinia(createPinia())
    const projects = useProjectStore()
    projects.projects = [project]
  })

  afterEach(() => vi.restoreAllMocks())

  it('renders the anomaly card, flags the spike day, and switches module', async () => {
    vi.spyOn(dashboardApi, 'summary').mockResolvedValue(summary)
    const anomaliesSpy = vi.spyOn(statsApi, 'anomalies').mockResolvedValue(buildAnomalyResult())

    const wrapper = mount(DashboardView)
    await flushPromises()

    expect(anomaliesSpy).toHaveBeenCalledWith('PRJ-001', 'safety')
    expect(wrapper.text()).toContain('异常波动检测')
    expect(wrapper.text()).toContain('1 / 30 天')
    expect(wrapper.findAll('.bar.spike')).toHaveLength(1)

    const qualityButton = wrapper.findAll('.module-toggle button').find((candidate) => candidate.text() === '质量')
    await qualityButton!.trigger('click')
    await flushPromises()
    expect(anomaliesSpy).toHaveBeenLastCalledWith('PRJ-001', 'quality')
  })

  it('shows degraded text when anomaly detection has no data', async () => {
    vi.spyOn(dashboardApi, 'summary').mockResolvedValue(summary)
    vi.spyOn(statsApi, 'anomalies').mockResolvedValue({
      ...buildAnomalyResult(),
      available: false,
      reason: '该时间段内没有记录',
      anomaly_days: 0,
      samples: [],
    })

    const wrapper = mount(DashboardView)
    await flushPromises()

    expect(wrapper.text()).toContain('该时间段内没有记录')
    expect(wrapper.findAll('.bar.spike')).toHaveLength(0)
  })
})
