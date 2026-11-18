import { apiClient } from './apiClient'
import type {
  ActivityFeedEntry,
  DashboardSummary,
  EmployeeProfile,
  EmployeeRankingEntry,
  ExceptionEntry,
  RecentChecklistEntry,
  WeeklyTrendPoint,
} from '../types/dashboard'

export interface DashboardFilterParams {
  // "YYYY-MM-DD" (ver utils/dateTime.ts::toISODateString).
  startDate?: string
  endDate?: string
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
}

export async function getDashboardSummary(params: DashboardFilterParams = {}): Promise<DashboardSummary> {
  const response = await apiClient.get<DashboardSummary>('/dashboard/summary', {
    params: { start_date: params.startDate, end_date: params.endDate, store_id: params.storeId },
  })
  return response.data
}

export async function getDashboardRanking(
  params: DashboardFilterParams & { limit?: number; sectorId?: number } = {},
): Promise<EmployeeRankingEntry[]> {
  const response = await apiClient.get<EmployeeRankingEntry[]>('/dashboard/ranking', {
    params: {
      start_date: params.startDate,
      end_date: params.endDate,
      store_id: params.storeId,
      sector_id: params.sectorId,
      limit: params.limit,
    },
  })
  return response.data
}

export async function getDashboardWeeklyTrend(params: DashboardFilterParams = {}): Promise<WeeklyTrendPoint[]> {
  const response = await apiClient.get<WeeklyTrendPoint[]>('/dashboard/weekly-trend', {
    params: { start_date: params.startDate, end_date: params.endDate, store_id: params.storeId },
  })
  return response.data
}

// "Raio-X Individual" — perfil analítico de um funcionário no período
// filtrado (não aceita storeId: a loja já vem implícita no funcionário).
export async function getEmployeeProfile(
  employeeId: number,
  params: Pick<DashboardFilterParams, 'startDate' | 'endDate'> = {},
): Promise<EmployeeProfile> {
  const response = await apiClient.get<EmployeeProfile>(`/dashboard/employees/${employeeId}/profile`, {
    params: { start_date: params.startDate, end_date: params.endDate },
  })
  return response.data
}

export async function getActivityFeed(
  params: { storeId?: number; limit?: number; startDate?: string; endDate?: string } = {},
): Promise<ActivityFeedEntry[]> {
  const response = await apiClient.get<ActivityFeedEntry[]>('/dashboard/activity-feed', {
    params: {
      store_id: params.storeId,
      limit: params.limit,
      start_date: params.startDate,
      end_date: params.endDate,
    },
  })
  return response.data
}

// "Alertas e Exceções" — tarefas do período marcadas como não
// realizadas ou com uma observação livre.
export async function getDashboardExceptions(
  params: DashboardFilterParams & { limit?: number } = {},
): Promise<ExceptionEntry[]> {
  const response = await apiClient.get<ExceptionEntry[]>('/dashboard/exceptions', {
    params: {
      start_date: params.startDate,
      end_date: params.endDate,
      store_id: params.storeId,
      limit: params.limit,
    },
  })
  return response.data
}

export async function getRecentChecklists(
  params: { storeId?: number; limit?: number; startDate?: string; endDate?: string } = {},
): Promise<RecentChecklistEntry[]> {
  const response = await apiClient.get<RecentChecklistEntry[]>('/dashboard/recent-checklists', {
    params: {
      store_id: params.storeId,
      limit: params.limit,
      start_date: params.startDate,
      end_date: params.endDate,
    },
  })
  return response.data
}
