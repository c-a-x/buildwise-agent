<script setup lang="ts">
import { ref } from 'vue'

import AssessmentTab from '@/components/green/AssessmentTab.vue'
import CarbonAccountingTab from '@/components/green/CarbonAccountingTab.vue'
import EnvLedgerTab from '@/components/green/EnvLedgerTab.vue'
import TrendTab from '@/components/green/TrendTab.vue'

type GreenTab = 'carbon' | 'assessment' | 'env' | 'trend'

const tabs: Array<{ key: GreenTab; label: string }> = [
  { key: 'carbon', label: '碳排核算' },
  { key: 'assessment', label: '四节一环保评估' },
  { key: 'env', label: '环保监测台账' },
  { key: 'trend', label: '碳排趋势' },
]

const activeTab = ref<GreenTab>('carbon')
</script>

<template>
  <div>
    <div class="green-module-bar">
      <div class="module-toggle" aria-label="绿色建造模块切换">
        <button v-for="tab in tabs" :key="tab.key" type="button" :class="{ active: activeTab === tab.key }" @click="activeTab = tab.key">{{ tab.label }}</button>
      </div>
    </div>
    <CarbonAccountingTab v-if="activeTab === 'carbon'" />
    <AssessmentTab v-else-if="activeTab === 'assessment'" />
    <EnvLedgerTab v-else-if="activeTab === 'env'" />
    <TrendTab v-else-if="activeTab === 'trend'" />
  </div>
</template>

<style scoped>
.green-module-bar { display: flex; justify-content: space-between; align-items: center; margin-bottom: 18px; }
.module-toggle { display: inline-flex; gap: 4px; padding: 3px; border: 1px solid var(--line); border-radius: 8px; background: var(--surface-soft); }
.module-toggle button { min-height: 44px; padding: 4px 12px; border: 0; border-radius: 6px; background: transparent; color: var(--muted); font-size: 11px; font-weight: 600; cursor: pointer; }
.module-toggle button.active { background: var(--surface); color: var(--primary); box-shadow: var(--shadow-sm); }
@media (max-width: 640px) { .module-toggle { width: 100%; display: flex; } .module-toggle button { flex: 1; padding: 4px 6px; font-size: 10px; } }
</style>
