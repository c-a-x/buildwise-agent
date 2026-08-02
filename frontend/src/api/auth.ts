import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { LoginPayload, LoginResponse, RegisterPayload, User } from '@/types/auth'

export const authApi = {
  async login(payload: LoginPayload): Promise<LoginResponse> {
    const response = await http.post<ApiEnvelope<LoginResponse>>('/auth/login', payload)
    return response.data.data
  },
  async register(payload: RegisterPayload): Promise<User> {
    const response = await http.post<ApiEnvelope<User>>('/auth/register', payload)
    return response.data.data
  },
  async me(): Promise<User> {
    const response = await http.get<ApiEnvelope<User>>('/auth/me')
    return response.data.data
  },
  async logout(): Promise<void> {
    await http.post('/auth/logout')
  },
}
