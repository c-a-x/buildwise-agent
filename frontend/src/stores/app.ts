import { ref } from 'vue'
import { defineStore } from 'pinia'

export const useAppStore = defineStore('app', () => {
  const sidebarCollapsed = ref(false)
  const mobileNavOpen = ref(false)
  const notice = ref('')

  function toggleSidebar(): void {
    if (typeof window !== 'undefined' && window.innerWidth <= 900) {
      mobileNavOpen.value = !mobileNavOpen.value
      return
    }
    sidebarCollapsed.value = !sidebarCollapsed.value
  }

  function closeMobileNav(): void {
    mobileNavOpen.value = false
  }

  function showNotice(message: string): void {
    notice.value = message
    window.setTimeout(() => {
      if (notice.value === message) notice.value = ''
    }, 4000)
  }

  return { sidebarCollapsed, mobileNavOpen, notice, toggleSidebar, closeMobileNav, showNotice }
})
