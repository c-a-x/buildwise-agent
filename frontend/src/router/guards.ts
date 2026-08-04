import type { NavigationGuard } from 'vue-router'

import type { Role } from '@/types/api'
import { useAuthStore } from '@/stores/auth'

declare module 'vue-router' {
  interface RouteMeta {
    requiresAuth?: boolean
    title?: string
    roles?: Role[]
  }
}

export const authGuard: NavigationGuard = async (to) => {
  const auth = useAuthStore()

  if (to.meta.requiresAuth) {
    if (!auth.user && auth.token) await auth.restoreSession()
    if (!auth.isAuthenticated) return { name: 'login', query: { redirect: to.fullPath } }
    if (to.meta.roles && !to.meta.roles.includes(auth.user?.role as Role)) return { name: 'forbidden' }
  }

  if ((to.name === 'login' || to.name === 'register') && auth.isAuthenticated) return { name: 'dashboard' }
}

