import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { greenApi } from '@/api/green'
import { projectsApi } from '@/api/projects'
import type { CarbonAnalysisResult, GreenBenchmark } from '@/types/green'
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

const materialFactor = {
  code: 'CONCRETE_C30',
  category: 'material' as const,
  name: 'C30商品混凝土',
  unit: 'm3',
  factor: 0.295,
  factor_unit: 'tCO2e/m3',
  source: 'GB/T 51366-2019',
  year: 2019,
  verified: false,
  note: '',
}

const gridFactor = {
  code: 'GRID_ELEC',
  category: 'energy' as const,
  name: '外购电力（全国电网平均）',
  unit: 'kWh',
  factor: 0.0005703,
  factor_unit: 'tCO2/kWh',
  source: '生态环境部',
  year: 2022,
  verified: true,
  note: '',
}

const analysisResult: CarbonAnalysisResult = {
  analysis_id: 'CAR-TEST-001',
  project_id: 'PRJ-001',
  project_name: '演示项目',
  created_at: '2026-08-05T10:00:00Z',
  area_m2: 8500,
  scope: '',
  total_emission: 640.1,
  unit: 'tCO2e',
  intensity: 0.0753,
  stages: [
    { stage: 'A1-A3', stage_name: '建材生产', emission: 534.5, share: 0.835, items_count: 2 },
    { stage: 'A4', stage_name: '建材运输', emission: 2.9412, share: 0.0046, items_count: 1 },
    { stage: 'A5', stage_name: '施工过程', emission: 102.654, share: 0.1604, items_count: 1 },
  ],
  items: [],
  top_contributors: [],
  suggestions: [],
  factor_version: '0.1.0',
  has_unverified_factors: true,
  factor_warnings: [],
  report_preview: '',
  is_simulated: true,
}

const benchmarkResult: GreenBenchmark = {
  available: true,
  reason: null,
  count: 2,
  metric: 'intensity',
  unit: 'tCO2e/m²',
  mean: 0.0877,
  std: 0.0175,
  current: { rank: 1, project_id: 'PRJ-001', project_name: '演示项目', intensity: 0.0753, z: -0.71, better_than_pct: 50 },
  items: [
    { rank: 1, project_id: 'PRJ-001', project_name: '演示项目', intensity: 0.0753, z: -0.71, better_than_pct: 50 },
    { rank: 2, project_id: 'PRJ-002', project_name: '对比项目', intensity: 0.1, z: 0.71, better_than_pct: 0 },
  ],
}

describe('GreenConstructionView', () => {
  afterEach(() => vi.restoreAllMocks())

  it('renders the carbon accounting form with stage sections and factor options', async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project])
    vi.spyOn(greenApi, 'factors').mockResolvedValue([materialFactor, gridFactor])
    vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
    vi.spyOn(greenApi, 'benchmark').mockResolvedValue(benchmarkResult)

    const wrapper = mount(GreenConstructionView)
    await flushPromises()

    expect(wrapper.text()).toContain('碳排核算')
    expect(wrapper.text()).toContain('材料清单')
    expect(wrapper.text()).toContain('运输记录')
    expect(wrapper.text()).toContain('施工能耗')
    expect(wrapper.text()).toContain('A1-A3')
    expect(wrapper.text()).toContain('A4')
    expect(wrapper.text()).toContain('A5')
    expect(wrapper.text()).toContain('开始碳排核算')

    // 添加一条材料后，因子下拉中应出现已加载的排放因子
    const addMaterial = wrapper.findAll('button').find((candidate) => candidate.text().includes('添加一条材料'))
    await addMaterial!.trigger('click')
    await flushPromises()
    expect(wrapper.text()).toContain('C30商品混凝土')
  })

  it('shows analysis results including stages and report preview', async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project])
    vi.spyOn(greenApi, 'factors').mockResolvedValue([materialFactor, gridFactor])
    vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
    vi.spyOn(greenApi, 'benchmark').mockResolvedValue(benchmarkResult)

    const wrapper = mount(GreenConstructionView)
    await flushPromises()
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('请至少填写一条材料、运输或能耗记录')
  })

  it('renders the dynamic carbon ring with animated total and stage breakdown after analysis', async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project])
    vi.spyOn(greenApi, 'factors').mockResolvedValue([materialFactor, gridFactor])
    vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
    vi.spyOn(greenApi, 'benchmark').mockResolvedValue(benchmarkResult)
    vi.spyOn(greenApi, 'analyze').mockResolvedValue(analysisResult)

    const wrapper = mount(GreenConstructionView)
    await flushPromises()

    const fillSample = wrapper.findAll('button').find((candidate) => candidate.text().includes('填入示例清单'))
    await fillSample!.trigger('click')
    await flushPromises()

    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('分阶段排放占比')
    expect(wrapper.text()).toContain('A1-A3 · 建材生产')
    expect(wrapper.text()).toContain('A5 · 施工过程')
    expect(wrapper.text()).toContain('640.10')
    expect(wrapper.text()).toContain('tCO2e')
  })

  it('downloads the Word report as a file from the result area', async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project])
    vi.spyOn(greenApi, 'factors').mockResolvedValue([materialFactor, gridFactor])
    vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
    vi.spyOn(greenApi, 'benchmark').mockResolvedValue(benchmarkResult)
    vi.spyOn(greenApi, 'analyze').mockResolvedValue(analysisResult)
    vi.spyOn(greenApi, 'downloadReport').mockResolvedValue(new Blob(['docx'], { type: 'application/octet-stream' }))

    const createObjectURL = vi.fn(() => 'blob:mock-report')
    const revokeObjectURL = vi.fn()
    const originalCreate = URL.createObjectURL
    const originalRevoke = URL.revokeObjectURL
    Object.defineProperty(URL, 'createObjectURL', { value: createObjectURL, writable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: revokeObjectURL, writable: true })

    const wrapper = mount(GreenConstructionView)
    await flushPromises()

    const fillSample = wrapper.findAll('button').find((candidate) => candidate.text().includes('填入示例清单'))
    await fillSample!.trigger('click')
    await flushPromises()

    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    const downloadButton = wrapper.findAll('button').find((candidate) => candidate.text().includes('下载 Word 报告'))
    expect(downloadButton).toBeDefined()
    await downloadButton!.trigger('click')
    await flushPromises()

    expect(greenApi.downloadReport).toHaveBeenCalledWith('CAR-TEST-001')
    expect(createObjectURL).toHaveBeenCalledTimes(1)
    expect(revokeObjectURL).toHaveBeenCalledWith('blob:mock-report')

    Object.defineProperty(URL, 'createObjectURL', { value: originalCreate, writable: true })
    Object.defineProperty(URL, 'revokeObjectURL', { value: originalRevoke, writable: true })
  })

  it('renders the peer benchmark card with rank and z-score after analysis', async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project])
    vi.spyOn(greenApi, 'factors').mockResolvedValue([materialFactor, gridFactor])
    vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
    vi.spyOn(greenApi, 'analyze').mockResolvedValue(analysisResult)
    vi.spyOn(greenApi, 'benchmark').mockResolvedValue(benchmarkResult)

    const wrapper = mount(GreenConstructionView)
    await flushPromises()

    const fillSample = wrapper.findAll('button').find((candidate) => candidate.text().includes('填入示例清单'))
    await fillSample!.trigger('click')
    await flushPromises()
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('同类项目对标')
    expect(wrapper.text()).toContain('第 1 名')
    expect(wrapper.text()).toContain('优于 50%')
    expect(wrapper.text()).toContain('z=-0.71')
    expect(greenApi.benchmark).toHaveBeenCalledWith('PRJ-001')
  })

  it('shows degraded fallback text when benchmark has too few samples', async () => {
    setActivePinia(createPinia())
    localStorage.clear()
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project])
    vi.spyOn(greenApi, 'factors').mockResolvedValue([materialFactor, gridFactor])
    vi.spyOn(greenApi, 'analyses').mockResolvedValue([])
    vi.spyOn(greenApi, 'analyze').mockResolvedValue(analysisResult)
    vi.spyOn(greenApi, 'benchmark').mockResolvedValue({
      available: false,
      reason: '样本不足（1 个项目），至少需要 2 个项目',
      count: 1,
      metric: 'intensity',
      unit: 'tCO2e/m²',
      mean: null,
      std: null,
      current: null,
      items: [],
    })

    const wrapper = mount(GreenConstructionView)
    await flushPromises()

    const fillSample = wrapper.findAll('button').find((candidate) => candidate.text().includes('填入示例清单'))
    await fillSample!.trigger('click')
    await flushPromises()
    await wrapper.find('.primary-button').trigger('click')
    await flushPromises()

    expect(wrapper.text()).toContain('样本不足')
  })
})
