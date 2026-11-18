export interface StoreSettings {
  store_id: number
  max_assignees_per_task: number | null
  // Liga/desliga a aba de checklists do tablet operacional desta loja.
  operational_checklists_enabled: boolean
  auto_logout_minutes: number
  hide_task_timer: boolean
  require_live_photo_only: boolean
  require_pin_on_complete: boolean
  enable_audio_alerts: boolean
  shifts: string[]
}
