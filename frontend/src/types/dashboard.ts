// Espelha app/schemas/dashboard.py (backend) — métricas do painel de BI.
import type { Shift } from './checklistExecution'
import type { DayOfWeek } from './taskAssignment'

export interface DashboardSummary {
  total_tasks: number
  completed_tasks: number
  pending_tasks: number
  // Percentual (0-100), não fração.
  completion_rate: number
  checklist_divergent_count: number
}

export interface EmployeeRankingEntry {
  employee_id: number
  employee_name: string
  completed_count: number
  avg_execution_seconds: number | null
  on_time_count: number
  late_count: number
  // Percentual (0-100) entre as tarefas que tinham SLA configurado; nulo se
  // nenhuma das concluídas tinha estimated_duration_minutes.
  on_time_rate: number | null
}

export interface WeeklyTrendPoint {
  day_of_week: DayOfWeek
  completed_count: number
  avg_execution_seconds: number | null
}

export interface EmployeeProfileTaskEntry {
  id: number
  task_title: string
  started_at: string
  completed_at: string
  result: 'FEITO' | 'NAO_FEITO'
  estimated_duration_minutes: number | null
  duration_seconds: number
  // Nulo se a tarefa não tinha tempo estimado configurado.
  on_time: boolean | null
  // motivo digitado pelo funcionário, se algum.
  justification: string | null
  observation: string | null
  photo_url: string | null
}

// "Raio-X Individual" — drill-down de um funcionário no ranking.
export interface EmployeeProfile {
  employee_id: number
  employee_name: string
  completed_count: number
  avg_execution_seconds: number | null
  on_time_count: number
  late_count: number
  on_time_rate: number | null
  tasks: EmployeeProfileTaskEntry[]
}

// Uma linha do "Radar Ao Vivo" — sempre relativa a hoje.
export interface ActivityFeedEntry {
  id: string
  actor_name: string
  description: string
  occurred_at: string
}

export interface ExceptionEntry {
  id: string
  type: 'TAREFA' | 'CHECKLIST' | 'IMPEDIMENTO'
  title: string
  user_name: string
  date: string
  reason: string | null
}

// "Últimos Checklists" — sempre os mais recentes, com as
// "assinaturas" de quem executou e quem validou cada item.
export interface RecentChecklistEntry {
  id: number
  template_name: string
  shift: Shift
  status: 'IN_PROGRESS' | 'COMPLETED'
  fully_validated: boolean
  executed_by_name: string
  validated_by_names: string[]
  started_at: string
  finished_at: string | null
}
