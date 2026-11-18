import { apiClient } from './apiClient'
import type { Sector } from '../types/sector'

export interface ListSectorsParams {
  activeOnly?: boolean
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
}

export async function listSectors(params: ListSectorsParams = {}): Promise<Sector[]> {
  const response = await apiClient.get<Sector[]>('/sectors', {
    params: { active_only: params.activeOnly ?? false, store_id: params.storeId },
  })
  return response.data
}

export interface CreateSectorPayload {
  name: string
  // Obrigatório só quando quem cria é MASTER (ver app/core/deps.py::resolve_scoped_store_id).
  store_id?: number
}

export async function createSector(payload: CreateSectorPayload): Promise<Sector> {
  const response = await apiClient.post<Sector>('/sectors', payload)
  return response.data
}

export interface UpdateSectorPayload {
  name?: string
  active?: boolean
}

export async function updateSector(sectorId: number, payload: UpdateSectorPayload): Promise<Sector> {
  const response = await apiClient.patch<Sector>(`/sectors/${sectorId}`, payload)
  return response.data
}

export async function deleteSector(sectorId: number): Promise<Sector> {
  const response = await apiClient.delete<Sector>(`/sectors/${sectorId}`)
  return response.data
}
