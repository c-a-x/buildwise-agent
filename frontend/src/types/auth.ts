import type { Role } from './api'

export interface User {
  id: string
  username: string
  real_name: string
  role: Role
  phone: string | null
  is_active: boolean
}

export interface LoginResponse {
  access_token: string
  token_type: string
  expires_in: number
  user: User
}

export interface LoginPayload {
  username: string
  password: string
  remember?: boolean
}

export interface RegisterPayload {
  username: string
  real_name: string
  password: string
  password_confirm: string
  role: Exclude<Role, 'admin'>
  phone?: string
}

export interface ProfileUpdatePayload {
  real_name?: string
  phone?: string | null
}

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
  new_password_confirm: string
}

export interface ChangePasswordResponse {
  changed: boolean
}
