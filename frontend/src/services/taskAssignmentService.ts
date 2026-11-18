import { apiClient } from './apiClient'
import type { DayOfWeek, TaskAssignment, TaskAssignmentStatus, TaskResult } from '../types/taskAssignment'

export interface ListTaskAssignmentsParams {
  dayOfWeek?: DayOfWeek
  status?: TaskAssignmentStatus
  sectorId?: number
  shift?: string
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
}

export async function listTaskAssignments(params: ListTaskAssignmentsParams = {}): Promise<TaskAssignment[]> {
  const response = await apiClient.get<TaskAssignment[]>('/task-assignments', {
    params: {
      day_of_week: params.dayOfWeek,
      status: params.status,
      sector_id: params.sectorId,
      shift: params.shift,
      store_id: params.storeId,
    },
  })
  return response.data
}

export interface CreateTaskAssignmentPayload {
  task_id: number
  day_of_week: DayOfWeek
  sector_id: number
  shift: string
}

export async function createTaskAssignment(payload: CreateTaskAssignmentPayload): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>('/task-assignments', payload)
  return response.data
}

export interface UpdateTaskAssignmentPayload {
  day_of_week?: DayOfWeek
  sector_id?: number
  // Omitido = não altera (mesmo padrão de day_of_week/sector_id acima).
  shift?: string
}

export async function updateTaskAssignment(
  assignmentId: number,
  payload: UpdateTaskAssignmentPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.patch<TaskAssignment>(`/task-assignments/${assignmentId}`, payload)
  return response.data
}

export async function deleteTaskAssignment(assignmentId: number): Promise<void> {
  await apiClient.delete(`/task-assignments/${assignmentId}`)
}

export interface TaskAssignmentActionPayload {
  employee_id: number
  pin: string
}

export type StartTaskAssignmentPayload = TaskAssignmentActionPayload

export async function startTaskAssignment(
  assignmentId: number,
  payload: StartTaskAssignmentPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`/task-assignments/${assignmentId}/start`, payload)
  return response.data
}

export async function joinTaskAssignment(
  assignmentId: number,
  payload: TaskAssignmentActionPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`/task-assignments/${assignmentId}/join`, payload)
  return response.data
}

export interface LeaveTaskAssignmentPayload extends TaskAssignmentActionPayload {
  leave_reason?: string
}

export async function leaveTaskAssignment(
  assignmentId: number,
  payload: LeaveTaskAssignmentPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`/task-assignments/${assignmentId}/leave`, payload)
  return response.data
}

export interface CompleteTaskAssignmentPayload {
  employee_id: number
  pin: string
  result: TaskResult
  justification?: string
  // Sempre opcional, mesmo quando result é FEITO.
  observation?: string
  photo_url?: string
  extra_photo_urls?: string[]
}

export async function completeTaskAssignment(
  assignmentId: number,
  payload: CompleteTaskAssignmentPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`/task-assignments/${assignmentId}/complete`, payload)
  return response.data
}

export interface UploadTaskAssignmentPhotoPayload {
  employee_id: number
  pin: string
  photo: File
}

export interface UploadTaskAssignmentPhotoResponse {
  photo_url: string
}

export async function uploadTaskAssignmentPhoto(
  assignmentId: number,
  payload: UploadTaskAssignmentPhotoPayload,
): Promise<UploadTaskAssignmentPhotoResponse> {
  const formData = new FormData()
  formData.append('employee_id', String(payload.employee_id))
  formData.append('pin', payload.pin)
  formData.append('photo', payload.photo)

  const response = await apiClient.post<UploadTaskAssignmentPhotoResponse>(
    `/task-assignments/${assignmentId}/photo`,
    formData,
  )
  return response.data
}

export interface BlockTaskAssignmentPayload extends TaskAssignmentActionPayload {
  reason: string
}

export async function blockTaskAssignment(
  assignmentId: number,
  payload: BlockTaskAssignmentPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`/task-assignments/${assignmentId}/block`, payload)
  return response.data
}

export type ResumeTaskAssignmentPayload = TaskAssignmentActionPayload

export async function resumeTaskAssignment(
  assignmentId: number,
  payload: ResumeTaskAssignmentPayload,
): Promise<TaskAssignment> {
  const response = await apiClient.post<TaskAssignment>(`/task-assignments/${assignmentId}/resume`, payload)
  return response.data
}
