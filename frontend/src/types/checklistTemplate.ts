// Espelha app/schemas/checklist_template.py (backend) — catálogo de
// checklists de passagem de turno.
export interface ChecklistTemplateItem {
  id: number
  template_id: number
  description: string
  order_index: number
  required: boolean
  requires_photo: boolean
  active: boolean
}

export interface ChecklistTemplate {
  id: number
  store_id: number
  name: string
  active: boolean
  created_by_user_id: number
  target_sector_id: number | null
  shift: string
  created_at: string
  items: ChecklistTemplateItem[]
}
