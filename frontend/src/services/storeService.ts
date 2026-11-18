import { apiClient } from './apiClient'
import type { Store } from '../types/store'

// GET /stores é restrito a MASTER no backend — só chamar isso quando
// `user.role === 'MASTER'` (ver TaskFormModal/EmployeeFormModal/StoresPage).
export async function listStores(): Promise<Store[]> {
  const response = await apiClient.get<Store[]>('/stores')
  return response.data
}

export async function getStore(storeId: number): Promise<Store> {
  const response = await apiClient.get<Store>(`/stores/${storeId}`)
  return response.data
}

export interface CreateStorePayload {
  name: string
  brand?: string
}

export async function createStore(payload: CreateStorePayload): Promise<Store> {
  const response = await apiClient.post<Store>('/stores', payload)
  return response.data
}

export interface UpdateStorePayload {
  name?: string
  brand?: string | null
  active?: boolean
}

export async function updateStore(storeId: number, payload: UpdateStorePayload): Promise<Store> {
  const response = await apiClient.patch<Store>(`/stores/${storeId}`, payload)
  return response.data
}
