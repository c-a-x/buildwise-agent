import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type DOMWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { greenApi } from '@/api/green'
import { useProjectStore } from '@/stores/project'
import type { EnvRecord, EnvThreshold, GreenAdvice, GreenAssessmentResult, GreenBenchmark, GreenReference, GreenTarget, GreenTrend } from '@/types/green'
import GreenConstructionView from '@/views/green/GreenConstructionView.vue'

const project = {
  id: 'PRJ-001',
  code: 'DEMO-001',
  name: '演示项目',
  address: '演示地址',
  description: '',
  status: 'active',
  manager_user_id: 'USR-001',
}

const referenceResult: GreenReference = {
  version: '0.1.0',
  updated_at: '2026-08-01T00:00:00Z',
  source_note: '',
  groups: [],
}

const benchmarkResult: GreenBenchmark = {
  available: false,
  reason: '样本不足（1 个项目），至少需要 2 个项目',
  count: 1,
  metric: 'intensity',
  unit: 'tCO2e/m²',
  mean: null,
  std: null,
  current: null,
  items: [],
}

const assessmentResult: GreenAssessmentResult = {
  assessment_id: 'GAS-TEST-001',
  project_id: 'PRJ-001',
  project_name: '演示项目',
  title: '主体结构阶段评估',
  area_m2: 8500,
  total_score: 88,
  level: '优秀',
  dimensions: [
    {
      dimension: 'material',
      name: '节材',
      score: 90,
      metrics: [
        { key: 'recycled_material_pct', name: '可循环材料利用率', value: 30, target: 30, direction: 'higher', score: 100 },
        { key: 'template_reuse_times', name: '模板周转次数', value: 5, target: 6, direction: 'higher', score: 83 },
      ],
    },
  ],
  is_simulated: false,
  report_preview: '评估报告预览：本项目总体处于先进水平。',
  created_at: '2026-08-05T10:00:00Z',
}

const thresholds: EnvThreshold[] = [
  { key: 'pm25', name: 'PM2.5', unit: 'μg/m³', rule: 'above', limit: 75, min: null, max: null },
  { key: 'ph', name: 'pH', unit: '', rule: 'range', limit: null, min: 6, max: 9 },
]

const envRecord: EnvRecord = {
  record_id: 'ENV-TEST-001',
  project_id: 'PRJ-001',
  project_name: '演示项目',
  record_date: '2026-08-05',
  pm25: 120,
  pm10: 80,
  tsp: 200,
  noise_day_db: 60,
  noise_night_db: 50,
  cod_mg: 50,
  ss_mg: 30,
  ph: 7.2,
  solid_waste_t: 2.5,
  has_alerts: true,
  alerts: [{ key: 'pm25', name: 'PM2.5', value: 120, rule: 'above', limit: 75, min: null, max: null }],
  created_at: '2026-08-05T10:00:00Z',
}

const trendResult: GreenTrend = {
  project_id: 'PRJ-001',
  project_name: '演示项目',
  points: [
    { created_at: '2026-08-01T10:00:00Z', total_emission: 640, area_m2: 8500, intensity: 0.0753 },
    { created_at: '2026-08-08T10:00:00Z', total_emission: 580, area_m2: 8500, intensity: 0.0682 },
  ],
  current: { intensity: 0.0682, target_intensity: 0.1, grade: '达标', gap_pct: -31.8 },
}

const targetResult: GreenTarget = {
  project_id: 'PRJ-001',
  target_intensity: 0.1,
  note: '对标先进水平',
  updated_at: '2026-08-01T10:00:00Z',
}

const adviceResult: GreenAdvice = {
  advice: '1. 将模板周转次数提升至 6 次。\n2. 加大非传统水源利用率至 30%。',
  is_simulated: true,
  source_type: 'assessment',
  generated_at: '2026-08-11T10:00:00Z',
}

type ViewWrapper = ReturnType<typeof mount>

function mountView(): ViewWrapper {
  setActivePinia(createPinia())
  localStorage.clear()
  const projects = useProjectStore()
  projects.projects = [project]
  // 默认碳排 Tab 挂载时的依赖
  vi.spyOn(greenApi, 'factors').mockResolvedValue([])
  vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
  vi.spyOn(greenApi, 'reference').mockResolvedValue(referenceResult)
  vi.spyOn(greenApi, 'benchmark').mockResolvedValue(benchmarkResult)
  vi.spyOn(greenApi, 'assessments').mockResolvedValue([])
  return mount(GreenConstructionView)
}

function tabButton(wrapper: ViewWrapper, label: string): DOMWrapper<Element> {
  const button = wrapper.findAll('.module-toggle button').find((candidate) => candidate.text().includes(label))
  if (!button) throw new Error(`找不到 Tab：${label}`)
  return button
}

describe('GreenConstructionView 扩展 Tab', () => {
  afterEach(() => vi.restoreAllMocks())

  it('渲染四个绿色模块 Tab，并可切换到四节一环保评估', async () => {
    const wrapper = mountView()
    await flushPromises()

    const buttons = wrapper.findAll('.module-toggle button')
    expect(buttons).toHaveLength(4)
    expect(buttons.map((button) => button.text())).toEqual(['碳排核算', '四节一环保评估', '环保监测台账', '碳排趋势'])

    await tabButton(wrapper, '四节一环保评估').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('录入五维指标')
    expect(wrapper.text()).toContain('开始四节一环保评估')
  })

  it('提交评估后显示总分、等级与评估编号', async () => {
    vi.spyOn(greenApi, 'submitAssessment').mockResolvedValue(assessmentResult)
    const wrapper = mountView()
    await flushPromises()

    await tabButton(wrapper, '四节一环保评估').trigger('click')
    await flushPromises()

    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(greenApi.submitAssessment).toHaveBeenCalledWith(expect.objectContaining({ project_id: 'PRJ-001' }))
    expect(wrapper.text()).toContain('优秀')
    expect(wrapper.text()).toContain('GAS-TEST-001')
    expect(wrapper.text()).toContain('节材')
    expect(wrapper.text()).toContain('评估报告预览')
  })

  it('台账页用告警行与超标徽标渲染超标读数', async () => {
    vi.spyOn(greenApi, 'envThresholds').mockResolvedValue(thresholds)
    vi.spyOn(greenApi, 'envRecords').mockResolvedValue([envRecord])
    const wrapper = mountView()
    await flushPromises()

    await tabButton(wrapper, '环保监测台账').trigger('click')
    await flushPromises()

    expect(greenApi.envRecords).toHaveBeenCalledWith({ project_id: 'PRJ-001' })
    expect(wrapper.find('tr.alert-row').exists()).toBe(true)
    expect(wrapper.find('.status-pill.danger').text()).toContain('超标')
    expect(wrapper.find('.alert-cell').text()).toContain('120')
  })

  it('趋势页绘制强度折线与当前达标状态', async () => {
    vi.spyOn(greenApi, 'trend').mockResolvedValue(trendResult)
    vi.spyOn(greenApi, 'target').mockResolvedValue(targetResult)
    const wrapper = mountView()
    await flushPromises()

    await tabButton(wrapper, '碳排趋势').trigger('click')
    await flushPromises()

    expect(greenApi.trend).toHaveBeenCalledWith('PRJ-001')
    const polyline = wrapper.find('polyline.trend-line')
    expect(polyline.exists()).toBe(true)
    expect(polyline.attributes('points')).toBeTruthy()
    expect(wrapper.text()).toContain('达标')
    expect(wrapper.text()).toContain('核算明细')
  })

  it('评估后生成 AI 优化建议并显示演示徽标', async () => {
    vi.spyOn(greenApi, 'submitAssessment').mockResolvedValue(assessmentResult)
    vi.spyOn(greenApi, 'advice').mockResolvedValue(adviceResult)
    const wrapper = mountView()
    await flushPromises()

    await tabButton(wrapper, '四节一环保评估').trigger('click')
    await flushPromises()
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    const adviceButton = wrapper.findAll('button').find((candidate) => candidate.text().includes('生成 AI 优化建议'))
    expect(adviceButton).toBeDefined()
    await adviceButton!.trigger('click')
    await flushPromises()

    expect(greenApi.advice).toHaveBeenCalledWith(expect.objectContaining({ source_type: 'assessment', assessment_id: 'GAS-TEST-001' }))
    expect(wrapper.text()).toContain('提升至 6 次')
    expect(wrapper.text()).toContain('演示建议')
  })
})
