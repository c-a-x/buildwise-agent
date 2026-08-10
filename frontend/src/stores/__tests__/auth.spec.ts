import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { createPinia, setActivePinia } from 'pinia'

import { authApi } from '@/api/auth'
import { useAuthStore } from '@/stores/auth'
import type { User } from '@/types/auth'
import { setToken } from '@/utils/storage'

const user: User = {
  id: 'USR-002',
  username: 'safety',
  real_name: '演示安全员',
  role: 'safety_officer',
  phone: null,
  is_active: true,
}

describe('auth store', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
    setActivePinia(createPinia())
  })

  afterEach(() => vi.restoreAllMocks())

  it('keeps loading true while restoring a token session and clears it afterwards', async () => {
    setToken('stored-token')
    let resolveMe: (value: User) => void = () => undefined
    const mePromise = new Promise<User>((resolve) => { resolveMe = resolve })
    vi.spyOn(authApi, 'me').mockReturnValue(mePromise)
    const store = useAuthStore()

    const restore = store.restoreSession()
    expect(store.loading).toBe(true)
    resolveMe(user)
    await expect(restore).resolves.toBe(true)
    expect(store.loading).toBe(false)
    expect(store.user).toEqual(user)
  })

  it('clears the session and loading state when restore fails', async () => {
    setToken('expired-token')
    vi.spyOn(authApi, 'me').mockRejectedValue(new Error('expired'))
    const store = useAuthStore()

    await expect(store.restoreSession()).resolves.toBe(false)
    expect(store.loading).toBe(false)
    expect(store.token).toBeNull()
    expect(store.user).toBeNull()
    expect(localStorage.getItem('buildwise_access_token')).toBeNull()
  })
})
