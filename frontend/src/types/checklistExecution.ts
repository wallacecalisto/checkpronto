// Espelha app/schemas/checklist_execution.py (backend) — execução de um
// checklist por um turno específico + validação cruzada.
export type Shift = 'MANHA' | 'TARDE' | 'NOITE'
export type ChecklistItemResponse = 'OK' | 'DIVERGENTE'
export type ChecklistValidationResult = 'APROVADO' | 'DIVERGENTE'

export const SHIFTS: Shift[] = ['MANHA', 'TARDE', 'NOITE']

export const SHIFT_LABEL: Record<Shift, string> = {
  MANHA: 'Manhã',
  TARDE: 'Tarde',
  NOITE: 'Noite',
}

export function suggestedShift(now: Date = new Date()): Shift {
  const hour = now.getHours()
  if (hour < 12) return 'MANHA'
  if (hour < 18) return 'TARDE'
  return 'NOITE'
}

export interface ChecklistValidation {
  id: number
  checklist_execution_item_id: number
  validated_by_user_id: number
  validated_at: string
  result: ChecklistValidationResult
  justification: string | null
  original_response_snapshot: {
    item_description: string
    response: string | null
    observation: string | null
  }
}

export interface ChecklistExecutionItem {
  id: number
  checklist_execution_id: number
  template_item_id: number
  item_description_snapshot: string
  response: ChecklistItemResponse | null
  observation: string | null
  photo_url: string | null
  extra_photo_urls: string[]
  requires_photo: boolean
  validation: ChecklistValidation | null
}

export type ChecklistExecutionStatus = 'IN_PROGRESS' | 'COMPLETED'

export interface ChecklistExecution {
  id: number
  template_id: number
  template_name: string
  store_id: number
  shift: Shift
  executed_by_user_id: number | null
  executed_by_employee_id: number | null
  executed_by_name: string
  validated_by_names: string[]
  started_at: string
  finished_at: string | null
  status: ChecklistExecutionStatus
  fully_validated: boolean
  items: ChecklistExecutionItem[]
}
