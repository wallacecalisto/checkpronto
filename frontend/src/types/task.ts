export interface Task {
  id: number
  store_id: number
  title: string
  description: string | null
  // SLA opcional — nulo = a tarefa nunca é considerada "com
  // atraso" (ver types/dashboard.ts, TaskExecutionHistory no backend).
  estimated_duration_minutes: number | null
  requires_photo_proof: boolean
  active: boolean
  created_by_user_id: number
  created_at: string
}
