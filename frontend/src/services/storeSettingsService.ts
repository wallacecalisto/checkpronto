import { apiClient } from './apiClient'
import type { StoreSettings } from '../types/storeSettings'

export async function getStoreSettings(storeId: number): Promise<StoreSettings> {
  const response = await apiClient.get<StoreSettings>(`/stores/${storeId}/settings`)
  return response.data
}

export interface UpdateStoreSettingsPayload {
  max_assignees_per_task?: number | null
  operational_checklists_enabled?: boolean
  auto_logout_minutes?: number
  hide_task_timer?: boolean
  require_live_photo_only?: boolean
  require_pin_on_complete?: boolean
  enable_audio_alerts?: boolean
  shifts?: string[]
}

export async function updateStoreSettings(
  storeId: number,
  payload: UpdateStoreSettingsPayload,
): Promise<StoreSettings> {
  const response = await apiClient.patch<StoreSettings>(`/stores/${storeId}/settings`, payload)
  return response.data
}
