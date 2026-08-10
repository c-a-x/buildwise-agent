import { computed, ref } from 'vue'
import { defineStore } from 'pinia'

import { authApi } from '@/api/auth'
import { getApiError } from '@/api/http'
import type { ChangePasswordPayload, ChangePasswordResponse, LoginPayload, ProfileUpdatePayload, RegisterPayload, User } from '@/types/auth'
import { clearToken, getToken, setToken } from '@/utils/storage'

export const useAuthStore = defineStore('auth', () => {
  const token = ref<string | null>(getToken())
  const user = ref<User | null>(null)
  const loading = ref(false)
  const error = ref('')

  const isAuthenticated = computed(() => Boolean(token.value && user.value))

  async function login(payload: LoginPayload): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      const response = await authApi.login(payload)
      token.value = response.access_token
      user.value = response.user
      setToken(response.access_token, payload.remember !== false)
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function register(payload: RegisterPayload): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      await authApi.register(payload)
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function restoreSession(): Promise<boolean> {
    if (!token.value) return false
    loading.value = true
    error.value = ''
    try {
      user.value = await authApi.me()
      return true
    } catch {
      clearSession()
      return false
    } finally {
      loading.value = false
    }
  }

  async function logout(): Promise<void> {
    try {
      if (token.value) await authApi.logout()
    } catch {
      // The local session is still cleared when the server is unreachable.
    } finally {
      clearSession()
    }
  }

  async function updateProfile(payload: ProfileUpdatePayload): Promise<void> {
    loading.value = true
    error.value = ''
    try {
      user.value = await authApi.updateProfile(payload)
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  async function changePassword(payload: ChangePasswordPayload): Promise<ChangePasswordResponse> {
    loading.value = true
    error.value = ''
    try {
      return await authApi.changePassword(payload)
    } catch (cause) {
      error.value = getApiError(cause)
      throw cause
    } finally {
      loading.value = false
    }
  }

  function clearSession(): void {
    token.value = null
    user.value = null
    clearToken()
  }

  window.addEventListener('buildwise:auth-expired', clearSession)

  return { token, user, loading, error, isAuthenticated, login, register, restoreSession, logout, updateProfile, changePassword, clearSession }
})
