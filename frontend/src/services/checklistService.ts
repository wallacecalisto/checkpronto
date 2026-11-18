import { apiClient } from './apiClient'
import type {
  ChecklistExecution,
  ChecklistExecutionItem,
  ChecklistExecutionStatus,
  ChecklistItemResponse,
  ChecklistValidation,
  ChecklistValidationResult,
  Shift,
} from '../types/checklistExecution'

export interface ListChecklistExecutionsParams {
  templateId?: number
  shift?: Shift
  status?: ChecklistExecutionStatus
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
  // "YYYY-MM-DD" (ver utils/dateTime.ts::toISODateString) — filtro por
  // started_at, inclusive nas duas pontas.
  startedFrom?: string
  startedTo?: string
}

export async function listChecklistExecutions(
  params: ListChecklistExecutionsParams = {},
): Promise<ChecklistExecution[]> {
  const response = await apiClient.get<ChecklistExecution[]>('/checklists', {
    params: {
      template_id: params.templateId,
      shift: params.shift,
      status: params.status,
      store_id: params.storeId,
      started_from: params.startedFrom,
      started_to: params.startedTo,
    },
  })
  return response.data
}

export async function getChecklistExecution(executionId: number): Promise<ChecklistExecution> {
  const response = await apiClient.get<ChecklistExecution>(`/checklists/${executionId}`)
  return response.data
}

export interface StartChecklistExecutionPayload {
  template_id: number
  shift: Shift
  employee_id?: number
  pin?: string
}

export async function startChecklistExecution(payload: StartChecklistExecutionPayload): Promise<ChecklistExecution> {
  const response = await apiClient.post<ChecklistExecution>('/checklists', payload)
  return response.data
}

export interface AnswerChecklistItemPayload {
  response: ChecklistItemResponse
  observation?: string
  photo_url?: string
  extra_photo_urls?: string[]
}

export async function answerChecklistItem(
  executionId: number,
  itemId: number,
  payload: AnswerChecklistItemPayload,
): Promise<ChecklistExecutionItem> {
  const response = await apiClient.patch<ChecklistExecutionItem>(
    `/checklists/${executionId}/items/${itemId}`,
    payload,
  )
  return response.data
}

export interface UploadChecklistItemPhotoPayload {
  photo: File
}

export interface UploadChecklistItemPhotoResponse {
  photo_url: string
}

export async function uploadChecklistItemPhoto(
  executionId: number,
  itemId: number,
  payload: UploadChecklistItemPhotoPayload,
): Promise<UploadChecklistItemPhotoResponse> {
  const formData = new FormData()
  formData.append('photo', payload.photo)

  const response = await apiClient.post<UploadChecklistItemPhotoResponse>(
    `/checklists/${executionId}/items/${itemId}/photo`,
    formData,
  )
  return response.data
}

export async function completeChecklistExecution(executionId: number): Promise<ChecklistExecution> {
  const response = await apiClient.post<ChecklistExecution>(`/checklists/${executionId}/complete`)
  return response.data
}

export interface ValidateChecklistItemPayload {
  result: ChecklistValidationResult
  justification?: string
}

export async function validateChecklistItem(
  executionId: number,
  itemId: number,
  payload: ValidateChecklistItemPayload,
): Promise<ChecklistValidation> {
  const response = await apiClient.post<ChecklistValidation>(
    `/checklists/${executionId}/items/${itemId}/validate`,
    payload,
  )
  return response.data
}
