import { beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { authApi } from '@/api/auth'
import router from '@/router'
import { authGuard } from '@/router/guards'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types/auth'
import { setToken } from '@/utils/storage'

const safetyUser: User = {
  id: 'USR-002',
  username: 'safety',
  real_name: '演示安全员',
  role: 'safety_officer',
  phone: null,
  is_active: true,
}

beforeEach(() => {
  localStorage.clear()
  sessionStorage.clear()
  setActivePinia(createPinia())
  vi.restoreAllMocks()
})

describe('authGuard', () => {
  it('redirects unauthenticated users to login with the original path', async () => {
    const result = await authGuard({ fullPath: '/work-orders', meta: { requiresAuth: true } } as never, {} as never, undefined as never)
    expect(result).toEqual({ name: 'login', query: { redirect: '/work-orders' } })
  })

  it('restores a token session and rejects users without the required role', async () => {
    setToken('stored-token')
    vi.spyOn(authApi, 'me').mockResolvedValue(safetyUser)

    const result = await authGuard({ fullPath: '/settings', meta: { requiresAuth: true, roles: ['admin'] } } as never, {} as never, undefined as never)

    expect(authApi.me).toHaveBeenCalledOnce()
    expect(result).toEqual({ name: 'forbidden' })
  })

  it('allows an authenticated user to continue and sends them away from login', async () => {
    const auth = useAuthStore()
    auth.token = 'token'
    auth.user = safetyUser

    await expect(authGuard({ fullPath: '/safety/analyze', meta: { requiresAuth: true, roles: ['safety_officer'] } } as never, {} as never, undefined as never)).resolves.toBeUndefined()
    await expect(authGuard({ name: 'login', fullPath: '/login', meta: {} } as never, {} as never, undefined as never)).resolves.toEqual({ name: 'dashboard' })
  })

  it('clears the local session when the API reports an expired token', () => {
    const auth = useAuthStore()
    auth.token = 'expired-token'
    auth.user = safetyUser

    window.dispatchEvent(new CustomEvent('buildwise:auth-expired'))

    expect(auth.token).toBeNull()
    expect(auth.user).toBeNull()
  })
})

it('registers every planned application route', () => {
  const paths = new Set(router.getRoutes().map((route) => route.path))
  for (const path of ['/login', '/register', '/forgot-password', '/dashboard', '/projects', '/safety/analyze', '/safety/history', '/work-orders', '/work-orders/:id', '/worker-care', '/reports/daily', '/reports/history', '/quality', '/green', '/knowledge', '/profile', '/settings', '/403']) {
    expect(paths).toContain(path)
  }
})
