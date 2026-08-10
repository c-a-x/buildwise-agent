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
          capabilities: {
            vision: { key: 'vision', name: '视觉识别', provider: 'mock', status: 'simulated', is_simulated: true, reason: '离线模拟视觉', next_step: '配置真实模型' },
            retrieval: { key: 'retrieval', name: '规范检索', provider: 'local_keyword', status: 'available', is_simulated: false, reason: '本地关键词检索', next_step: '可选重建 Chroma' },
            text: { key: 'text', name: '文本生成', provider: 'template', status: 'simulated', is_simulated: true, reason: '离线模板生成', next_step: '配置 LLM' },
            speech: { key: 'speech', name: '语音转写', provider: 'off', status: 'not_configured', is_simulated: false, reason: '未配置语音 Provider', next_step: '使用浏览器语音或配置 ASR' },
            weather: { key: 'weather', name: '实时天气', provider: 'off', status: 'not_configured', is_simulated: false, reason: '未配置天气', next_step: '配置天气 API' },
            tts: { key: 'tts', name: '语音合成', provider: 'off', status: 'not_configured', is_simulated: false, reason: '未配置 TTS', next_step: '配置 edge-tts' },
            broadcast: { key: 'broadcast', name: '硬件广播', provider: 'webhook', status: 'configured', is_simulated: false, reason: '广播 webhook 已配置', next_step: '运行广播 smoke test' },
          },
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
    expect(wrapper.text()).toContain('离线模拟')
    expect(wrapper.text()).toContain('未配置语音 Provider')
    expect(wrapper.text()).toContain('已配置（待验证）')
    expect(wrapper.text()).not.toContain('后续接入项')
  })

  it('keeps rendering when an older health response has no capabilities', async () => {
    vi.spyOn(http, 'get').mockResolvedValue({
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

    expect(wrapper.text()).toContain('运行配置')
    expect(wrapper.text()).not.toContain('读取失败')
  })
})
