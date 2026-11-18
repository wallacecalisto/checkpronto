import { apiClient } from './apiClient'
import type { ChecklistTemplate, ChecklistTemplateItem } from '../types/checklistTemplate'

export interface ListChecklistTemplatesParams {
  activeOnly?: boolean
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
  sectorId?: number
}

export async function listChecklistTemplates(params: ListChecklistTemplatesParams = {}): Promise<ChecklistTemplate[]> {
  const response = await apiClient.get<ChecklistTemplate[]>('/checklist-templates', {
    params: { active_only: params.activeOnly, store_id: params.storeId, sector_id: params.sectorId },
  })
  return response.data
}

export async function getChecklistTemplate(templateId: number): Promise<ChecklistTemplate> {
  const response = await apiClient.get<ChecklistTemplate>(`/checklist-templates/${templateId}`)
  return response.data
}

export interface CreateChecklistTemplateItemPayload {
  description: string
  order_index?: number
  required?: boolean
  requires_photo?: boolean
}

export interface CreateChecklistTemplatePayload {
  name: string
  // Obrigatório só quando quem cria é MASTER.
  store_id?: number
  target_sector_id?: number
  shift: string
  items: CreateChecklistTemplateItemPayload[]
}

export async function createChecklistTemplate(payload: CreateChecklistTemplatePayload): Promise<ChecklistTemplate> {
  const response = await apiClient.post<ChecklistTemplate>('/checklist-templates', payload)
  return response.data
}

export interface UpdateChecklistTemplatePayload {
  name?: string
  active?: boolean
  target_sector_id?: number | null
  shift?: string
}

export async function updateChecklistTemplate(
  templateId: number,
  payload: UpdateChecklistTemplatePayload,
): Promise<ChecklistTemplate> {
  const response = await apiClient.patch<ChecklistTemplate>(`/checklist-templates/${templateId}`, payload)
  return response.data
}

export async function deleteChecklistTemplate(templateId: number): Promise<ChecklistTemplate> {
  const response = await apiClient.delete<ChecklistTemplate>(`/checklist-templates/${templateId}`)
  return response.data
}

export async function createChecklistTemplateItem(
  templateId: number,
  payload: CreateChecklistTemplateItemPayload,
): Promise<ChecklistTemplateItem> {
  const response = await apiClient.post<ChecklistTemplateItem>(`/checklist-templates/${templateId}/items`, payload)
  return response.data
}

export interface UpdateChecklistTemplateItemPayload {
  description?: string
  order_index?: number
  required?: boolean
  requires_photo?: boolean
  active?: boolean
}

export async function updateChecklistTemplateItem(
  itemId: number,
  payload: UpdateChecklistTemplateItemPayload,
): Promise<ChecklistTemplateItem> {
  const response = await apiClient.patch<ChecklistTemplateItem>(`/checklist-template-items/${itemId}`, payload)
  return response.data
}
