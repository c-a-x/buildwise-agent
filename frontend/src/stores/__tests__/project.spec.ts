import { afterEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { projectsApi } from '@/api/projects'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/project'

const project: Project = {
  id: 'PRJ-001',
  code: 'DEMO-001',
  name: '演示项目',
  address: '演示地址',
  description: '',
  status: 'active',
  manager_user_id: 'USR-001',
}

describe('project store', () => {
  afterEach(() => vi.restoreAllMocks())

  it('creates a project, refreshes the list, and selects the new project', async () => {
    setActivePinia(createPinia())
    const created: Project = { ...project, id: 'PRJ-002', code: 'NEW-001', name: '新建项目' }
    vi.spyOn(projectsApi, 'create').mockResolvedValue(created)
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project, created])

    const store = useProjectStore()
    await store.createProject({ code: 'NEW-001', name: '新建项目', address: '新建地址', description: '' })

    expect(store.projects).toEqual([project, created])
    expect(store.currentProjectId).toBe('PRJ-002')
    expect(store.error).toBe('')
  })

  it('exposes a readable API error when project creation fails', async () => {
    setActivePinia(createPinia())
    vi.spyOn(projectsApi, 'create').mockRejectedValue(new Error('项目编码已存在'))

    const store = useProjectStore()
    await expect(store.createProject({ code: 'DUP-001', name: '重复项目', address: '地址', description: '' })).rejects.toThrow('项目编码已存在')

    expect(store.error).toBe('项目编码已存在')
  })

  it('keeps loading true while createProject waits for its nested refresh', async () => {
    setActivePinia(createPinia())
    let resolveList: (value: Project[]) => void = () => undefined
    const listPromise = new Promise<Project[]>((resolve) => { resolveList = resolve })
    const created: Project = { ...project, id: 'PRJ-002', code: 'NEW-001', name: '新建项目' }
    vi.spyOn(projectsApi, 'create').mockResolvedValue(created)
    vi.spyOn(projectsApi, 'list').mockReturnValue(listPromise)

    const store = useProjectStore()
    const request = store.createProject({ code: 'NEW-001', name: '新建项目', address: '新地址', description: '' })
    await vi.waitFor(() => expect(projectsApi.list).toHaveBeenCalledOnce())

    expect(store.loading).toBe(true)
    resolveList([project, created])
    await request
    expect(store.loading).toBe(false)
  })

  it('rejects when the post-create refresh fails and exposes the refresh error', async () => {
    setActivePinia(createPinia())
    vi.spyOn(projectsApi, 'create').mockResolvedValue({ ...project, id: 'PRJ-002' })
    vi.spyOn(projectsApi, 'list').mockRejectedValue(new Error('项目列表刷新失败'))

    const store = useProjectStore()
    await expect(store.createProject({ code: 'NEW-001', name: '新建项目', address: '新地址', description: '' })).rejects.toThrow('项目列表刷新失败')

    expect(store.error).toBe('项目列表刷新失败')
    expect(store.loading).toBe(false)
  })
})
