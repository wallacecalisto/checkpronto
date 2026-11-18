
export type DayOfWeek = 'MONDAY' | 'TUESDAY' | 'WEDNESDAY' | 'THURSDAY' | 'FRIDAY' | 'SATURDAY' | 'SUNDAY'
export type TaskAssignmentStatus = 'PENDING' | 'IN_PROGRESS' | 'COMPLETED' | 'BLOCKED'
export type TaskResult = 'FEITO' | 'NAO_FEITO'

export const DAYS_OF_WEEK: DayOfWeek[] = [
  'MONDAY',
  'TUESDAY',
  'WEDNESDAY',
  'THURSDAY',
  'FRIDAY',
  'SATURDAY',
  'SUNDAY',
]

export const DAY_OF_WEEK_LABEL: Record<DayOfWeek, string> = {
  MONDAY: 'Segunda-feira',
  TUESDAY: 'Terça-feira',
  WEDNESDAY: 'Quarta-feira',
  THURSDAY: 'Quinta-feira',
  FRIDAY: 'Sexta-feira',
  SATURDAY: 'Sábado',
  SUNDAY: 'Domingo',
}

export const DAY_OF_WEEK_SHORT_LABEL: Record<DayOfWeek, string> = {
  MONDAY: 'Seg',
  TUESDAY: 'Ter',
  WEDNESDAY: 'Qua',
  THURSDAY: 'Qui',
  FRIDAY: 'Sex',
  SATURDAY: 'Sáb',
  SUNDAY: 'Dom',
}

export function currentDayOfWeek(now: Date = new Date()): DayOfWeek {
  return DAYS_OF_WEEK[(now.getDay() + 6) % 7]
}

export interface TaskAssignmentParticipant {
  employee_id: number
  employee_name: string
  started_at: string
}

export interface TaskAssignment {
  id: number
  task_id: number
  store_id: number
  day_of_week: DayOfWeek
  // Denormalizados do catálogo (Task) só na resposta — ver backend.
  task_title: string
  task_description: string | null
  // SLA da tarefa — usado para colorir o cronômetro ao vivo
  // quando o tempo corrido ultrapassa isso.
  estimated_duration_minutes: number | null
  requires_photo_proof: boolean
  shift: string
  sector_id: number
  sector_name: string
  status: TaskAssignmentStatus
  started_at: string | null
  completed_at: string | null
  started_by_employee_id: number | null
  completed_by_employee_id: number | null
  started_by_user_id: number | null
  completed_by_user_id: number | null
  result: TaskResult | null
  justification: string | null
  observation: string | null
  photo_url: string | null
  extra_photo_urls: string[]
  elapsed_seconds: number | null
  active_participants: TaskAssignmentParticipant[]
  blocked_at: string | null
  block_reason: string | null
  blocked_by_employee_id: number | null
  latest_execution_history_id: number | null
}
