import { afterEach, describe, expect, it, vi } from 'vitest'
import { flushPromises, mount, type VueWrapper } from '@vue/test-utils'
import { createPinia, setActivePinia } from 'pinia'

import { projectsApi } from '@/api/projects'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import type { Project } from '@/types/project'
import ProjectListView from '@/views/projects/ProjectListView.vue'

const project: Project = {
  id: 'PRJ-001',
  code: 'DEMO-001',
  name: '演示项目',
  address: '演示地址',
  description: '',
  status: 'active',
  manager_user_id: 'USR-001',
}

const createdProject: Project = {
  ...project,
  id: 'PRJ-002',
  code: 'NEW-001',
  name: '新建项目',
  address: '新建地址',
  description: '新建描述',
  manager_user_id: 'USR-ADMIN',
}

function prepare(role: 'admin' | 'project_manager' | 'safety_officer') {
  setActivePinia(createPinia())
  const auth = useAuthStore()
  auth.user = {
    id: 'USR-ADMIN',
    username: 'manager',
    real_name: '项目管理员',
    role,
    phone: null,
    is_active: true,
  }
  const projects = useProjectStore()
  projects.projects = [project]
  return { projects }
}

const mountedWrappers: VueWrapper[] = []

function mountView(): VueWrapper {
  const wrapper = mount(ProjectListView, { attachTo: document.body, global: { stubs: { RouterLink: true } } })
  mountedWrappers.push(wrapper)
  return wrapper
}

describe('ProjectListView', () => {
  afterEach(() => {
    mountedWrappers.forEach((wrapper) => wrapper.unmount())
    mountedWrappers.length = 0
    vi.restoreAllMocks()
  })

  it('opens an accessible dialog and moves focus to the first input', async () => {
    prepare('admin')
    const wrapper = mountView()
    const trigger = wrapper.find('[data-test="create-project"]')

    await trigger.trigger('click')
    await flushPromises()

    const dialog = wrapper.find('[role="dialog"]')
    expect(dialog.attributes('aria-modal')).toBe('true')
    expect(dialog.attributes('aria-labelledby')).toBe('project-dialog-title')
    expect(document.activeElement).toBe(wrapper.find('#project-code').element)
  })

  it('lets admin create a project through the existing API and selects it after refresh', async () => {
    const { projects } = prepare('admin')
    vi.spyOn(projectsApi, 'create').mockResolvedValue(createdProject)
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project, createdProject])

    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    await wrapper.find('#project-code').setValue('NEW-001')
    await wrapper.find('#project-name').setValue('新建项目')
    await wrapper.find('#project-address').setValue('新建地址')
    await wrapper.find('#project-description').setValue('新建描述')
    await wrapper.find('[data-test="project-form"]').trigger('submit')
    await flushPromises()

    expect(projectsApi.create).toHaveBeenCalledWith({ code: 'NEW-001', name: '新建项目', address: '新建地址', description: '新建描述' })
    expect(projects.currentProjectId).toBe('PRJ-002')
    expect(wrapper.text()).toContain('新建项目')
    expect(wrapper.find('[data-test="project-form"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.find('[data-test="create-project"]').element)
  })

  it('shows API errors and keeps the dialog open after a failed submission', async () => {
    prepare('project_manager')
    vi.spyOn(projectsApi, 'create').mockRejectedValue(new Error('项目编码已存在'))
    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    await wrapper.find('#project-code').setValue('DUP-001')
    await wrapper.find('#project-name').setValue('重复项目')
    await wrapper.find('#project-address').setValue('地址')
    await wrapper.find('[data-test="project-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[role="alert"]').text()).toContain('项目编码已存在')
    expect(wrapper.find('[role="dialog"]').exists()).toBe(true)
    expect(wrapper.find('[data-test="project-submit"]').attributes('disabled')).toBeUndefined()
  })

  it('disables dialog actions while the create request is pending', async () => {
    prepare('admin')
    let resolveCreate: (value: Project) => void = () => undefined
    const createPromise = new Promise<Project>((resolve) => { resolveCreate = resolve })
    vi.spyOn(projectsApi, 'create').mockReturnValue(createPromise)
    vi.spyOn(projectsApi, 'list').mockResolvedValue([project, createdProject])
    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    await wrapper.find('#project-code').setValue('NEW-001')
    await wrapper.find('#project-name').setValue('新建项目')
    await wrapper.find('#project-address').setValue('新建地址')
    await wrapper.find('[data-test="project-form"]').trigger('submit')
    await flushPromises()

    expect(wrapper.find('[data-test="project-submit"]').attributes('disabled')).toBeDefined()
    expect(wrapper.find('[data-test="project-cancel"]').attributes('disabled')).toBeDefined()
    resolveCreate(createdProject)
    await flushPromises()
  })

  it('closes with cancel and restores focus to the trigger', async () => {
    prepare('project_manager')
    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    await wrapper.find('[data-test="project-cancel"]').trigger('click')
    await flushPromises()

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.find('[data-test="create-project"]').element)
  })

  it('closes with Escape and restores focus to the trigger', async () => {
    prepare('admin')
    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    window.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape' }))
    await flushPromises()

    expect(wrapper.find('[role="dialog"]').exists()).toBe(false)
    expect(document.activeElement).toBe(wrapper.find('[data-test="create-project"]').element)
  })

  it('wraps Tab and Shift+Tab within the dialog focusable controls', async () => {
    prepare('admin')
    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    await flushPromises()

    const dialog = wrapper.find('[role="dialog"]')
    const first = wrapper.find('[aria-label="关闭新建项目窗口"]')
    const last = wrapper.find('[data-test="project-submit"]')

    ;(last.element as HTMLElement).focus()
    await dialog.trigger('keydown', { key: 'Tab' })
    expect(document.activeElement).toBe(first.element)

    ;(first.element as HTMLElement).focus()
    dialog.element.dispatchEvent(new KeyboardEvent('keydown', { bubbles: true, key: 'Tab', shiftKey: true }))
    expect(document.activeElement).toBe(last.element)
  })

  it('shows validation feedback and does not submit incomplete project data', async () => {
    prepare('project_manager')
    const createSpy = vi.spyOn(projectsApi, 'create')
    const wrapper = mountView()
    await wrapper.find('[data-test="create-project"]').trigger('click')
    await wrapper.find('[data-test="project-form"]').trigger('submit')

    expect(wrapper.text()).toContain('请填写项目编码、名称和地址')
    expect(createSpy).not.toHaveBeenCalled()
  })

  it('hides the creation action for users without project management permission', () => {
    prepare('safety_officer')
    const wrapper = mountView()

    expect(wrapper.find('[data-test="create-project"]').exists()).toBe(false)
  })
})
