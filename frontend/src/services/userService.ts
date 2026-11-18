import { apiClient } from './apiClient'
import type { User, UserRole } from '../types/auth'

// Toda a rota /users é estritamente MASTER no backend (nem GESTOR/LIDER têm
// acesso) — só chamar isso quando `user.role === 'MASTER'`.
export async function listUsers(): Promise<User[]> {
  const response = await apiClient.get<User[]>('/users')
  return response.data
}

export interface CreateUserPayload {
  name: string
  email: string
  password: string
  role: UserRole
  // Obrigatório para todo papel exceto MASTER (que é sempre global).
  store_id?: number
}

export async function createUser(payload: CreateUserPayload): Promise<User> {
  const response = await apiClient.post<User>('/users', payload)
  return response.data
}

export interface UpdateUserPayload {
  name?: string
  role?: UserRole
  store_id?: number
  active?: boolean
  // Opcional: redefine a senha diretamente (não há fluxo "esqueci minha senha").
  password?: string
}

export async function updateUser(userId: number, payload: UpdateUserPayload): Promise<User> {
  const response = await apiClient.patch<User>(`/users/${userId}`, payload)
  return response.data
}

export async function deleteUser(userId: number): Promise<User> {
  const response = await apiClient.delete<User>(`/users/${userId}`)
  return response.data
}
