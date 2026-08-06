<script setup lang="ts">
export type IconName =
  | 'dashboard'
  | 'project'
  | 'shield'
  | 'history'
  | 'clipboard'
  | 'worker'
  | 'report'
  | 'quality'
  | 'leaf'
  | 'book'
  | 'user'
  | 'settings'
  | 'bell'
  | 'search'
  | 'plus'
  | 'arrow'
  | 'chevron'
  | 'upload'
  | 'check'
  | 'close'
  | 'info'
  | 'menu'
  | 'refresh'
  | 'calendar'
  | 'filter'
  | 'lock'
  | 'logout'
  | 'spark'
  | 'clock'
  | 'download'
  | 'mic'
  | 'camera'
  | 'speaker'

const props = withDefaults(defineProps<{ name: IconName; size?: number }>(), { size: 18 })
</script>

<template>
  <svg class="app-icon" :width="props.size" :height="props.size" viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="1.8" stroke-linecap="round" stroke-linejoin="round" aria-hidden="true">
    <template v-if="props.name === 'dashboard'">
      <rect x="3" y="3" width="7" height="7" rx="1" /><rect x="14" y="3" width="7" height="7" rx="1" /><rect x="3" y="14" width="7" height="7" rx="1" /><rect x="14" y="14" width="7" height="7" rx="1" />
    </template>
    <template v-else-if="props.name === 'project'"><path d="m3 7 9-4 9 4-9 4-9-4Z" /><path d="M3 12 12 16l9-4M3 17l9 4 9-4" /></template>
    <template v-else-if="props.name === 'shield'"><path d="M12 3 20 6v5c0 5-3.3 8.4-8 10-4.7-1.6-8-5-8-10V6l8-3Z" /><path d="m8.5 12 2.2 2.2 4.8-5" /></template>
    <template v-else-if="props.name === 'history'"><path d="M3 12a9 9 0 1 0 3-6.7L3 8.5" /><path d="M3 3v5.5h5.5M12 7v5l3 2" /></template>
    <template v-else-if="props.name === 'clipboard'"><rect x="5" y="4" width="14" height="17" rx="2" /><path d="M9 4V3h6v1M8 9h8M8 13h6M8 17h4" /></template>
    <template v-else-if="props.name === 'worker'"><circle cx="12" cy="8" r="3" /><path d="M5 21a7 7 0 0 1 14 0M4 6h16M6 3h12v4H6z" /></template>
    <template v-else-if="props.name === 'report'"><path d="M5 3h10l4 4v14H5z" /><path d="M15 3v5h4M8 12h8M8 16h8" /></template>
    <template v-else-if="props.name === 'quality'"><path d="m12 3 2.5 5.2L20 9l-4 4 .9 5.7-4.9-2.5-4.9 2.5L8 13 4 9l5.5-.8L12 3Z" /><path d="m9.5 11.5 1.7 1.7 3.3-3.4" /></template>
    <template v-else-if="props.name === 'leaf'"><path d="M20 4C10 4 5 8 5 14c0 3 2 5 5 5 6 0 10-5 10-15Z" /><path d="M4 21c3-5 7-8 13-10" /></template>
    <template v-else-if="props.name === 'book'"><path d="M4 5.5A2.5 2.5 0 0 1 6.5 3H20v17H6.5A2.5 2.5 0 0 0 4 22V5.5Z" /><path d="M4 5.5V22M8 7h8M8 11h7" /></template>
    <template v-else-if="props.name === 'user'"><circle cx="12" cy="8" r="3.5" /><path d="M4.5 21a7.5 7.5 0 0 1 15 0" /></template>
    <template v-else-if="props.name === 'settings'"><path d="M12 8.5a3.5 3.5 0 1 0 0 7 3.5 3.5 0 0 0 0-7Z" /><path d="m19.4 15 .1.1a2 2 0 0 1-2.8 2.8l-.1-.1a2 2 0 0 0-3.4 1.4V19a2 2 0 0 1-4 0v-.2a2 2 0 0 0-3.4-1.4l-.1.1a2 2 0 0 1-2.8-2.8l.1-.1A2 2 0 0 0 1.7 11H2a2 2 0 0 1 0-4h.2a2 2 0 0 0 1.4-3.4l-.1-.1a2 2 0 0 1 2.8-2.8l.1.1A2 2 0 0 0 10 1.5V2a2 2 0 0 1 4 0v.2a2 2 0 0 0 3.4 1.4l.1-.1a2 2 0 0 1 2.8 2.8l-.1.1A2 2 0 0 0 19.5 10h.2a2 2 0 0 1 0 4h-.2a2 2 0 0 0-.1 1Z" /></template>
    <template v-else-if="props.name === 'bell'"><path d="M18 9a6 6 0 0 0-12 0c0 7-3 7-3 9h18c0-2-3-2-3-9M10 21h4" /></template>
    <template v-else-if="props.name === 'search'"><circle cx="11" cy="11" r="6.5" /><path d="m16 16 5 5" /></template>
    <template v-else-if="props.name === 'plus'"><path d="M12 5v14M5 12h14" /></template>
    <template v-else-if="props.name === 'arrow'"><path d="M5 12h14M13 6l6 6-6 6" /></template>
    <template v-else-if="props.name === 'chevron'"><path d="m9 5 7 7-7 7" /></template>
    <template v-else-if="props.name === 'upload'"><path d="M12 16V4M7 9l5-5 5 5M5 20h14" /></template>
    <template v-else-if="props.name === 'check'"><path d="m5 12 4 4L19 6" /></template>
    <template v-else-if="props.name === 'close'"><path d="m6 6 12 12M18 6 6 18" /></template>
    <template v-else-if="props.name === 'info'"><circle cx="12" cy="12" r="9" /><path d="M12 11v5M12 8h.01" /></template>
    <template v-else-if="props.name === 'menu'"><path d="M4 7h16M4 12h16M4 17h16" /></template>
    <template v-else-if="props.name === 'refresh'"><path d="M20 11a8 8 0 0 0-14-4L4 9M4 5v4h4M4 13a8 8 0 0 0 14 4l2-2M20 19v-4h-4" /></template>
    <template v-else-if="props.name === 'calendar'"><rect x="3" y="5" width="18" height="16" rx="2" /><path d="M16 3v4M8 3v4M3 10h18" /></template>
    <template v-else-if="props.name === 'filter'"><path d="M4 6h16M7 12h10M10 18h4" /></template>
    <template v-else-if="props.name === 'lock'"><rect x="5" y="10" width="14" height="11" rx="2" /><path d="M8 10V7a4 4 0 0 1 8 0v3" /></template>
    <template v-else-if="props.name === 'logout'"><path d="M10 5H5v14h5M14 8l4 4-4 4M18 12H9" /></template>
    <template v-else-if="props.name === 'spark'"><path d="m12 3 1.5 6.5L20 11l-6.5 1.5L12 19l-1.5-6.5L4 11l6.5-1.5L12 3ZM19 3v4M21 5h-4" /></template>
    <template v-else-if="props.name === 'clock'"><circle cx="12" cy="12" r="9" /><path d="M12 7v5l3 2" /></template>
    <template v-else-if="props.name === 'download'"><path d="M12 4v11M7 11l5 5 5-5M5 20h14" /></template>
    <template v-else-if="props.name === 'mic'"><rect x="8" y="3" width="8" height="12" rx="4" /><path d="M5 11a7 7 0 0 0 14 0M12 18v3M9 21h6" /></template>
    <template v-else-if="props.name === 'camera'"><path d="M3 8h3l2-3h8l2 3h3v12H3V8Z" /><circle cx="12" cy="13" r="3.5" /></template>
    <template v-else-if="props.name === 'speaker'"><path d="M4 10v4h3l5 4V6l-5 4H4Z" /><path d="M16 8.5a4.5 4.5 0 0 1 0 7M18.5 6a8 8 0 0 1 0 12" /></template>
  </svg>
</template>
