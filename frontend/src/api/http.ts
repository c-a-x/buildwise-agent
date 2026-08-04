import axios, { type AxiosError, type AxiosInstance } from 'axios'

import type { ApiErrorPayload } from '@/types/api'
import { clearToken, getToken } from '@/utils/storage'

const http: AxiosInstance = axios.create({
  baseURL: import.meta.env.VITE_API_BASE_URL || 'http://localhost:8000/api/v1',
  timeout: 30_000,
})

http.interceptors.request.use((config) => {
  const token = getToken()
  if (token) config.headers.Authorization = `Bearer ${token}`
  // 仅默认超时被 FormData 覆盖到 120s；实时检测等传显式短超时的请求保留原超时
  if (config.data instanceof FormData && config.timeout === http.defaults.timeout) {
    config.timeout = 120_000
  }
  return config
})

http.interceptors.response.use(
  (response) => response,
  (error: AxiosError<ApiErrorPayload>) => {
    if (error.response?.status === 401) {
      clearToken()
      window.dispatchEvent(new CustomEvent('buildwise:auth-expired'))
    }
    return Promise.reject(error)
  },
)

export function getApiError(error: unknown): string {
  if (axios.isAxiosError<ApiErrorPayload>(error)) {
    return error.response?.data?.message || error.message || '请求失败，请稍后重试'
  }
  return error instanceof Error ? error.message : '请求失败，请稍后重试'
}

export default http
