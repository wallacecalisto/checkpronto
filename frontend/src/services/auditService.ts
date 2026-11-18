import { apiClient } from './apiClient'
import type { AuditAction, AuditLog } from '../types/auditLog'

export interface ListAuditLogsParams {
  action?: AuditAction
  entityType?: string
  actorUserId?: number
  actorEmployeeId?: number
  // Só considerado pelo backend quando quem chama é MASTER.
  storeId?: number
  // "YYYY-MM-DD" (ver utils/dateTime.ts::toISODateString) — filtro por
  // created_at, inclusive nas duas pontas.
  dateFrom?: string
  dateTo?: string
}

export async function listAuditLogs(params: ListAuditLogsParams = {}): Promise<AuditLog[]> {
  const response = await apiClient.get<AuditLog[]>('/audit', {
    params: {
      action: params.action,
      entity_type: params.entityType,
      actor_user_id: params.actorUserId,
      actor_employee_id: params.actorEmployeeId,
      store_id: params.storeId,
      date_from: params.dateFrom,
      date_to: params.dateTo,
    },
  })
  return response.data
}
