import { apiClient } from './apiClient'
import type { User } from '../types/auth'

export interface ChangePasswordPayload {
  current_password: string
  new_password: string
}

export async function changePassword(payload: ChangePasswordPayload): Promise<User> {
  const response = await apiClient.post<User>('/auth/change-password', payload)
  return response.data
}
