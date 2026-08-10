<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, reactive, ref } from 'vue'

import AppIcon from '@/components/common/AppIcon.vue'
import AppPageHeader from '@/components/common/AppPageHeader.vue'
import AppState from '@/components/common/AppState.vue'
import { useAuthStore } from '@/stores/auth'
import { useProjectStore } from '@/stores/project'
import type { ProjectCreate } from '@/types/project'

const auth = useAuthStore()
const projects = useProjectStore()
const createPanelOpen = ref(false)
const formError = ref('')
const submitting = ref(false)
const form = reactive<ProjectCreate>({ code: '', name: '', address: '', description: '' })
const createTriggerRef = ref<HTMLButtonElement | null>(null)
const firstInputRef = ref<HTMLInputElement | null>(null)
const dialogRef = ref<HTMLElement | null>(null)
const canCreate = computed(() => ['admin', 'project_manager'].includes(auth.user?.role ?? ''))

const focusableSelector = 'a[href], button:not([disabled]), input:not([disabled]), select:not([disabled]), textarea:not([disabled]), [tabindex]:not([tabindex="-1"])'

function resetForm(): void {
  form.code = ''
  form.name = ''
  form.address = ''
  form.description = ''
  formError.value = ''
  projects.error = ''
}

function openCreatePanel(): void {
  resetForm()
  createPanelOpen.value = true
  void nextTick(() => firstInputRef.value?.focus())
}

function closeCreatePanel(): void {
  if (!submitting.value) {
    createPanelOpen.value = false
    void nextTick(() => createTriggerRef.value?.focus())
  }
}

function handleEscape(event: KeyboardEvent): void {
  if (event.key === 'Escape' && createPanelOpen.value) closeCreatePanel()
}

function handleDialogKeydown(event: KeyboardEvent): void {
  if (!createPanelOpen.value || event.key !== 'Tab') return
  const dialog = dialogRef.value
  if (!dialog) return

  const focusableElements = Array.from(dialog.querySelectorAll<HTMLElement>(focusableSelector))
  if (!focusableElements.length) return

  const first = focusableElements[0]
  const last = focusableElements[focusableElements.length - 1]
  if (!first || !last) return
  const activeElement = document.activeElement
  if ((!event.shiftKey && activeElement === last) || (event.shiftKey && activeElement === first)) {
    event.preventDefault()
    const target = event.shiftKey ? last : first
    target.focus()
  } else if (!dialog.contains(activeElement)) {
    event.preventDefault()
    const target = event.shiftKey ? last : first
    target.focus()
  }
}

async function submitCreate(): Promise<void> {
  formError.value = ''
  if (!form.code.trim() || !form.name.trim() || !form.address.trim()) {
    formError.value = '请填写项目编码、名称和地址'
    return
  }

  submitting.value = true
  try {
    await projects.createProject({
      code: form.code.trim(),
      name: form.name.trim(),
      address: form.address.trim(),
      description: form.description.trim(),
    })
    submitting.value = false
    closeCreatePanel()
  } catch {
    // The store exposes the API message in projects.error for the form.
  } finally {
    submitting.value = false
  }
}

onMounted(() => {
  if (!projects.projects.length) void projects.loadProjects()
  window.addEventListener('keydown', handleEscape)
})

onUnmounted(() => window.removeEventListener('keydown', handleEscape))
</script>

<template>
  <div>
    <AppPageHeader eyebrow="PROJECT PORTFOLIO" title="项目管理" description="查看当前账号可访问的项目、负责人和现场状态。">
      <template #actions>
        <button v-if="canCreate" ref="createTriggerRef" class="primary-button" type="button" data-test="create-project" @click="openCreatePanel">
          <AppIcon name="plus" :size="16" />新建项目
        </button>
      </template>
    </AppPageHeader>

    <AppState v-if="projects.loading && !projects.projects.length" type="loading" title="正在加载项目" />
    <AppState v-else-if="projects.error && !projects.projects.length" type="error" title="项目加载失败" :description="projects.error" />
    <AppState v-else-if="!projects.projects.length" title="暂无可访问项目" description="请联系管理员加入项目成员。" />
    <div v-else class="project-grid">
      <article v-for="project in projects.projects" :key="project.id" class="project-card">
        <div class="project-image"><span>{{ project.status === 'active' ? '进行中' : '已归档' }}</span></div>
        <div class="project-body">
          <span class="status-pill success">{{ project.code }}</span>
          <h3>{{ project.name }}</h3>
          <p>{{ project.address }}</p>
          <dl>
            <div><dt>项目负责人</dt><dd>{{ project.manager_user_id }}</dd></div>
            <div><dt>项目状态</dt><dd>安全闭环已启用</dd></div>
          </dl>
          <div class="progress"><span /></div>
          <footer class="project-foot">
            <span>现场数据持续同步</span>
            <RouterLink to="/dashboard" @click="projects.selectProject(project.id)">进入工作台 <AppIcon name="arrow" :size="13" /></RouterLink>
          </footer>
        </div>
      </article>
    </div>

    <div v-if="createPanelOpen" class="modal-backdrop" role="presentation" @click.self="closeCreatePanel">
      <section ref="dialogRef" class="project-dialog" role="dialog" aria-modal="true" aria-labelledby="project-dialog-title" @keydown="handleDialogKeydown">
        <header class="project-dialog-head">
          <div>
            <p class="section-kicker">PROJECT SETUP</p>
            <h2 id="project-dialog-title">新建项目</h2>
            <p>创建后会自动加入当前账号的项目列表。</p>
          </div>
          <button class="icon-button" type="button" aria-label="关闭新建项目窗口" :disabled="submitting" @click="closeCreatePanel"><AppIcon name="close" :size="16" /></button>
        </header>
        <form data-test="project-form" class="form-grid" @submit.prevent="submitCreate">
          <div class="two-fields">
            <div class="form-field"><label for="project-code">项目编码 <span>必填</span></label><input id="project-code" ref="firstInputRef" v-model="form.code" maxlength="32" autocomplete="off" placeholder="例如：BJ-001" /></div>
            <div class="form-field"><label for="project-name">项目名称 <span>必填</span></label><input id="project-name" v-model="form.name" maxlength="128" autocomplete="off" placeholder="例如：滨江住宅项目" /></div>
          </div>
          <div class="form-field"><label for="project-address">项目地址 <span>必填</span></label><input id="project-address" v-model="form.address" maxlength="255" autocomplete="street-address" placeholder="填写施工现场地址" /></div>
          <div class="form-field"><label for="project-description">项目描述 <span>选填</span></label><textarea id="project-description" v-model="form.description" maxlength="500" placeholder="补充项目规模、阶段或现场说明" /></div>
          <p v-if="formError || projects.error" class="error-text" role="alert">{{ formError || projects.error }}</p>
          <footer class="project-dialog-foot">
            <button class="secondary-button" type="button" data-test="project-cancel" :disabled="submitting" @click="closeCreatePanel">取消</button>
            <button class="primary-button" type="submit" data-test="project-submit" :disabled="submitting"><AppIcon v-if="submitting" name="refresh" :size="16" />{{ submitting ? '正在创建…' : '创建项目' }}</button>
          </footer>
        </form>
      </section>
    </div>
  </div>
</template>
