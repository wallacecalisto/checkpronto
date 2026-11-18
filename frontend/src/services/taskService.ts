import { apiClient } from './apiClient'
import type { Task } from '../types/task'

export interface ListTasksParams {
  activeOnly?: boolean
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
}

export async function listTasks(params: ListTasksParams = {}): Promise<Task[]> {
  const response = await apiClient.get<Task[]>('/tasks', {
    params: { active_only: params.activeOnly, store_id: params.storeId },
  })
  return response.data
}

export interface CreateTaskPayload {
  title: string
  description?: string
  estimated_duration_minutes?: number
  requires_photo_proof?: boolean
  // Obrigatório só quando quem cria é MASTER.
  store_id?: number
}

export async function createTask(payload: CreateTaskPayload): Promise<Task> {
  const response = await apiClient.post<Task>('/tasks', payload)
  return response.data
}

export interface UpdateTaskPayload {
  title?: string
  description?: string
  estimated_duration_minutes?: number | null
  requires_photo_proof?: boolean
  active?: boolean
}

export async function updateTask(taskId: number, payload: UpdateTaskPayload): Promise<Task> {
  const response = await apiClient.patch<Task>(`/tasks/${taskId}`, payload)
  return response.data
}

export async function deleteTask(taskId: number): Promise<Task> {
  const response = await apiClient.delete<Task>(`/tasks/${taskId}`)
  return response.data
}
