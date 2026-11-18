
export interface TaskTimelineParticipant {
  employee_id: number
  employee_name: string
  worked_duration_seconds: number
}

export interface TaskTimelineSessionEntry {
  employee_id: number
  employee_name: string
  started_at: string
  ended_at: string | null
  leave_reason: string | null
}

export interface TaskTimelineBlockEntry {
  blocked_by_employee_id: number
  blocked_by_employee_name: string
  reason: string
  started_at: string
  ended_at: string | null
}

export interface TaskExecutionTimeline {
  execution_group_id: string
  task_id: number
  task_title: string
  created_by_user_name: string
  estimated_duration_minutes: number | null
  started_at: string
  completed_at: string
  // Tempo de PAREDE da execução inteira — não confundir com o
  // worked_duration_seconds de cada participante (ver TaskTimelineParticipant).
  total_elapsed_seconds: number
  result: 'FEITO' | 'NAO_FEITO'
  justification: string | null
  observation: string | null
  photo_url: string | null
  extra_photo_urls: string[]
  participants: TaskTimelineParticipant[]
  sessions: TaskTimelineSessionEntry[]
  blocks: TaskTimelineBlockEntry[]
}
