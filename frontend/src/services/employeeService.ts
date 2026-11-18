import { apiClient } from './apiClient'
import type { Employee } from '../types/employee'

export async function listActiveEmployees(): Promise<Employee[]> {
  const response = await apiClient.get<Employee[]>('/employees', { params: { active_only: true } })
  return response.data
}

export interface ListEmployeesParams {
  activeOnly?: boolean
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
}

export async function listEmployees(params: ListEmployeesParams = {}): Promise<Employee[]> {
  const response = await apiClient.get<Employee[]>('/employees', {
    params: { active_only: params.activeOnly ?? false, store_id: params.storeId },
  })
  return response.data
}

export interface CreateEmployeePayload {
  name: string
  role_title?: string
  // Obrigatório só quando quem cria é MASTER (ver app/core/deps.py::resolve_scoped_store_id).
  store_id?: number
  sector_id: number
}

export async function createEmployee(payload: CreateEmployeePayload): Promise<Employee> {
  const response = await apiClient.post<Employee>('/employees', payload)
  return response.data
}

export interface UpdateEmployeePayload {
  name?: string
  role_title?: string | null
  sector_id?: number
  active?: boolean
}

export async function updateEmployee(employeeId: number, payload: UpdateEmployeePayload): Promise<Employee> {
  const response = await apiClient.patch<Employee>(`/employees/${employeeId}`, payload)
  return response.data
}

export async function deleteEmployee(employeeId: number): Promise<Employee> {
  const response = await apiClient.delete<Employee>(`/employees/${employeeId}`)
  return response.data
}

export interface PinActionResponse {
  employee_id: number
  name: string
}


// Cria o PIN no primeiro acesso. Só funciona se ainda não existir um.
export async function setupPin(employeeId: number, pin: string): Promise<PinActionResponse> {
  const response = await apiClient.post<PinActionResponse>(`/employees/${employeeId}/pin/setup`, { pin })
  return response.data
}

// Apaga o PIN do funcionário (has_pin volta a false) — restrito a GESTOR/LIDER
// no backend (nem MASTER tem acesso, por decisão explícita de produto).
export async function resetPin(employeeId: number): Promise<Employee> {
  const response = await apiClient.post<Employee>(`/employees/${employeeId}/pin/reset`)
  return response.data
}
