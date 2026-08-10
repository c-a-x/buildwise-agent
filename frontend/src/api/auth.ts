import http from './http'
import type { ApiEnvelope } from '@/types/api'
import type { ChangePasswordPayload, ChangePasswordResponse, LoginPayload, LoginResponse, ProfileUpdatePayload, RegisterPayload, User } from '@/types/auth'

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
  async updateProfile(payload: ProfileUpdatePayload): Promise<User> {
    const response = await http.patch<ApiEnvelope<User>>('/users/me', payload)
    return response.data.data
  },
  async changePassword(payload: ChangePasswordPayload): Promise<ChangePasswordResponse> {
    const response = await http.post<ApiEnvelope<ChangePasswordResponse>>('/users/me/password', payload)
    return response.data.data
  },
}
