// Espelha app/schemas/audit_log.py (backend) — trilha de auditoria.
import { DAY_OF_WEEK_LABEL } from './taskAssignment'

export type AuditActorType = 'USER' | 'EMPLOYEE'

export type AuditAction =
  | 'CREATE'
  | 'UPDATE'
  | 'ACTIVATE'
  | 'DEACTIVATE'
  | 'START'
  | 'COMPLETE'
  | 'VALIDATE'
  | 'DELETE'
  | 'RESET_PIN'
  | 'RESET_PASSWORD'

export const AUDIT_ACTION_LABEL: Record<AuditAction, string> = {
  CREATE: 'Criação',
  UPDATE: 'Edição',
  ACTIVATE: 'Ativação',
  DEACTIVATE: 'Desativação',
  START: 'Início',
  COMPLETE: 'Conclusão',
  VALIDATE: 'Validação',
  DELETE: 'Exclusão',
  RESET_PIN: 'Reset de PIN',
  RESET_PASSWORD: 'Redefinição de senha',
}

export const AUDIT_ENTITY_TYPE_LABEL: Record<string, string> = {
  EMPLOYEE: 'Funcionário',
  TASK: 'Tarefa',
  TASK_ASSIGNMENT: 'Agendamento',
  USER: 'Usuário',
  CHECKLIST_TEMPLATE: 'Template de checklist',
  CHECKLIST_TEMPLATE_ITEM: 'Item de template',
  CHECKLIST_EXECUTION: 'Execução de checklist',
  CHECKLIST_VALIDATION: 'Validação de checklist',
}

export const AUDIT_FIELD_LABEL: Record<string, string> = {
  name: 'Nome',
  title: 'Título',
  description: 'Descrição',
  active: 'Status',
  role_title: 'Cargo',
  email: 'E-mail',
  role: 'Papel',
  store_id: 'Loja',
  day_of_week: 'Dia da semana',
  sector_id: 'Setor',
  assigned_employee_id: 'Funcionário atribuído',
  items: 'Itens',
  order_index: 'Ordem',
  required: 'Obrigatório',
  status: 'Status',
  finished_at: 'Concluído em',
  result: 'Resultado',
  justification: 'Justificativa',
  checklist_execution_item_id: 'Item do checklist',
  template_id: 'Template',
  shift: 'Turno',
}

export function auditFieldLabel(key: string): string {
  return AUDIT_FIELD_LABEL[key] ?? key
}

const AUDIT_VALUE_LABEL: Record<string, Record<string, string>> = {
  day_of_week: DAY_OF_WEEK_LABEL,
  status: {
    PENDING: 'Pendente',
    IN_PROGRESS: 'Em andamento',
    COMPLETED: 'Concluído',
  },
}

export function auditValueLabel(key: string, value: unknown): string | null {
  if (typeof value !== 'string') return null
  return AUDIT_VALUE_LABEL[key]?.[value] ?? null
}

const ENTITY_NAME_FIELD: Record<string, string> = {
  EMPLOYEE: 'name',
  TASK: 'title',
  USER: 'name',
  CHECKLIST_TEMPLATE: 'name',
  CHECKLIST_TEMPLATE_ITEM: 'description',
}

export function entityDisplayName(entry: AuditLog): string | null {
  const field = ENTITY_NAME_FIELD[entry.entity_type]
  if (!field) return null
  const value = entry.after_data?.[field] ?? entry.before_data?.[field]
  return typeof value === 'string' ? value : null
}

export interface AuditLog {
  id: number
  store_id: number | null
  store_name: string | null
  actor_type: AuditActorType
  actor_user_id: number | null
  actor_employee_id: number | null
  actor_name: string
  action: AuditAction
  entity_type: string
  entity_id: number
  before_data: Record<string, unknown> | null
  after_data: Record<string, unknown> | null
  created_at: string
}
