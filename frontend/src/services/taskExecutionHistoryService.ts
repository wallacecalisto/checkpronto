import { apiClient } from './apiClient'
import type { TaskExecutionTimeline } from '../types/taskExecutionTimeline'

export async function getExecutionTimeline(historyId: number): Promise<TaskExecutionTimeline> {
  const response = await apiClient.get<TaskExecutionTimeline>(`/task-execution-history/${historyId}/timeline`)
  return response.data
}
