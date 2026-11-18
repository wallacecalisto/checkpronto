import { useEffect, useState, type FormEvent, type ReactNode } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { ToggleSwitch } from '../../components/admin/ToggleSwitch'
import { useSelectedStore } from '../../contexts/SelectedStoreContext'
import { getApiErrorMessage } from '../../services/apiClient'
import { listStores } from '../../services/storeService'
import { getStoreSettings, updateStoreSettings } from '../../services/storeSettingsService'

function SettingsCard({ title, children }: { title: string; children: ReactNode }) {
  return (
    <section className="flex flex-col gap-1 rounded-2xl border border-gray-100/50 bg-white p-6 shadow-sm">
      <h2 className="mb-2 text-xs font-semibold uppercase tracking-wide text-gray-400">{title}</h2>
      <div className="flex flex-col divide-y divide-gray-100">{children}</div>
    </section>
  )
}

interface NumberFieldProps {
  id: string
  label: string
  description: string
  value: string
  onChange: (value: string) => void
  min: number
  placeholder?: string
}

interface ShiftsEditorProps {
  shifts: string[]
  onChange: (shifts: string[]) => void
}

function ShiftsEditor({ shifts, onChange }: ShiftsEditorProps) {
  const [newShiftInput, setNewShiftInput] = useState('')

  function addShift(): void {
    const trimmed = newShiftInput.trim()
    if (!trimmed || shifts.includes(trimmed)) {
      setNewShiftInput('')
      return
    }
    onChange([...shifts, trimmed])
    setNewShiftInput('')
  }

  function removeShift(shift: string): void {
    if (shifts.length <= 1) return
    onChange(shifts.filter((existing) => existing !== shift))
  }

  return (
    <div className="flex flex-col gap-2 py-3">
      <div className="flex flex-col gap-0.5">
        <p className="text-sm font-medium text-gray-800">Turnos da loja</p>
        <p className="text-xs text-gray-400">
          Alimenta o seletor de Turno ao cadastrar Tarefas e Checklists. Pelo menos um turno é obrigatório.
        </p>
      </div>
      <div className="flex flex-wrap gap-2">
        {shifts.map((shift) => (
          <span
            key={shift}
            className="flex items-center gap-1.5 rounded-full bg-indigo-50 py-1 pl-3 pr-1.5 text-sm font-medium text-indigo-700"
          >
            {shift}
            <button
              type="button"
              onClick={() => removeShift(shift)}
              disabled={shifts.length <= 1}
              aria-label={`Remover turno ${shift}`}
              className="rounded-full p-0.5 text-indigo-400 transition hover:bg-indigo-100 hover:text-indigo-700 disabled:cursor-not-allowed disabled:opacity-40"
            >
              ✕
            </button>
          </span>
        ))}
      </div>
      <div className="flex gap-2">
        <input
          value={newShiftInput}
          onChange={(event) => setNewShiftInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key !== 'Enter') return
            event.preventDefault()
            addShift()
          }}
          placeholder="Ex.: Abertura"
          aria-label="Novo turno"
          className="flex-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
        />
        <button
          type="button"
          onClick={addShift}
          className="shrink-0 rounded-lg border border-gray-200 px-3 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
        >
          Adicionar
        </button>
      </div>
    </div>
  )
}

function NumberField({ id, label, description, value, onChange, min, placeholder }: NumberFieldProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="text-sm font-medium text-gray-800">
          {label}
        </label>
        <p className="text-xs text-gray-400">{description}</p>
      </div>
      <input
        id={id}
        type="number"
        min={min}
        step={1}
        value={value}
        onChange={(event) => onChange(event.target.value)}
        placeholder={placeholder}
        className="w-24 shrink-0 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-right text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
      />
    </div>
  )
}

export function StoreSettingsPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const queryClient = useQueryClient()

  const { storeId: selectedStoreId, setStoreId: setSelectedStoreId } = useSelectedStore()
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })
  const effectiveStoreId = isMaster ? selectedStoreId : (user?.store_id ?? null)

  const settingsQuery = useQuery({
    queryKey: ['store-settings', effectiveStoreId],
    queryFn: () => getStoreSettings(effectiveStoreId as number),
    enabled: effectiveStoreId !== null,
  })

  const [maxAssigneesInput, setMaxAssigneesInput] = useState('')
  const [autoLogoutInput, setAutoLogoutInput] = useState('5')
  const [checklistsEnabled, setChecklistsEnabled] = useState(true)
  const [hideTaskTimer, setHideTaskTimer] = useState(false)
  const [enableAudioAlerts, setEnableAudioAlerts] = useState(false)
  const [requireLivePhotoOnly, setRequireLivePhotoOnly] = useState(false)
  const [requirePinOnComplete, setRequirePinOnComplete] = useState(false)
  const [shifts, setShifts] = useState<string[]>(['Manhã', 'Tarde', 'Noite'])
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [savedMessage, setSavedMessage] = useState(false)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    setErrorMessage(null)
    setSavedMessage(false)
  }, [effectiveStoreId])

  useEffect(() => {
    if (!settingsQuery.data) return
    setMaxAssigneesInput(
      settingsQuery.data.max_assignees_per_task != null ? String(settingsQuery.data.max_assignees_per_task) : '',
    )
    setAutoLogoutInput(String(settingsQuery.data.auto_logout_minutes))
    setChecklistsEnabled(settingsQuery.data.operational_checklists_enabled)
    setHideTaskTimer(settingsQuery.data.hide_task_timer)
    setEnableAudioAlerts(settingsQuery.data.enable_audio_alerts)
    setRequireLivePhotoOnly(settingsQuery.data.require_live_photo_only)
    setRequirePinOnComplete(settingsQuery.data.require_pin_on_complete)
    setShifts(settingsQuery.data.shifts)
  }, [settingsQuery.data])

  async function handleSubmit(event: FormEvent): Promise<void> {
    event.preventDefault()
    if (effectiveStoreId === null) return

    setErrorMessage(null)
    setSavedMessage(false)
    setIsSubmitting(true)
    try {
      const parsedMaxAssignees =
        maxAssigneesInput.trim() === '' ? null : Number.parseInt(maxAssigneesInput, 10)
      const parsedAutoLogout = Number.parseInt(autoLogoutInput, 10)

      const updated = await updateStoreSettings(effectiveStoreId, {
        max_assignees_per_task: Number.isNaN(parsedMaxAssignees as number) ? null : parsedMaxAssignees,
        operational_checklists_enabled: checklistsEnabled,
        auto_logout_minutes: Number.isNaN(parsedAutoLogout) ? 5 : parsedAutoLogout,
        hide_task_timer: hideTaskTimer,
        enable_audio_alerts: enableAudioAlerts,
        require_live_photo_only: requireLivePhotoOnly,
        require_pin_on_complete: requirePinOnComplete,
        shifts,
      })
      queryClient.setQueryData(['store-settings', effectiveStoreId], updated)
      setSavedMessage(true)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  const stores = storesQuery.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <div>
          <h1 className="text-xl font-semibold text-gray-900">Configurações da Loja</h1>
          <p className="text-sm text-gray-500">Regras que mudam o comportamento do sistema sem precisar de código.</p>
        </div>

        {isMaster && (
          <select
            value={selectedStoreId !== null ? String(selectedStoreId) : ''}
            onChange={(event) => setSelectedStoreId(event.target.value ? Number(event.target.value) : null)}
            className="w-fit rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="">Selecione uma loja…</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        )}
      </div>

      {isMaster && effectiveStoreId === null ? (
        <p className="text-center text-gray-500">Selecione uma loja acima para ver e editar as configurações dela.</p>
      ) : settingsQuery.isLoading ? (
        <p className="text-center text-gray-500">Carregando…</p>
      ) : (
        <form onSubmit={(event) => void handleSubmit(event)} className="flex max-w-2xl flex-col gap-5">
          <SettingsCard title="Regras de Operação">
            <NumberField
              id="max-assignees"
              label="Limite de pessoas por tarefa"
              description={'Quantas pessoas podem trabalhar ao mesmo tempo na mesma tarefa. Deixe em branco ou 0 para ilimitado — use 1 para o modelo "um funcionário por tarefa".'}
              value={maxAssigneesInput}
              onChange={setMaxAssigneesInput}
              min={0}
              placeholder="Ilimitado"
            />
            <NumberField
              id="auto-logout"
              label="Tempo de auto-logout (minutos)"
              description="Quanto tempo de inatividade no dispositivo até o sistema deslogar o funcionário automaticamente."
              value={autoLogoutInput}
              onChange={setAutoLogoutInput}
              min={1}
              placeholder="5"
            />
            <ShiftsEditor shifts={shifts} onChange={setShifts} />
          </SettingsCard>

          <SettingsCard title="Interface e Notificações">
            <ToggleSwitch
              id="checklists-enabled"
              label="Habilitar Checklists no Operacional"
              description="Mostra a aba de Checklists na tela operacional, além das Tarefas. Desligada, o funcionário só vê Tarefas."
              checked={checklistsEnabled}
              onChange={setChecklistsEnabled}
            />
            <ToggleSwitch
              id="hide-task-timer"
              label="Ocultar Cronômetro"
              description="Esconde o tempo estimado/decorrido das tarefas em andamento no Radar Ao Vivo da tela operacional."
              checked={hideTaskTimer}
              onChange={setHideTaskTimer}
            />
            <ToggleSwitch
              id="audio-alerts"
              label="Alertas Sonoros"
              description="Toca um som no dispositivo operacional ao concluir uma tarefa e quando uma tarefa em andamento estoura o prazo estimado."
              checked={enableAudioAlerts}
              onChange={setEnableAudioAlerts}
            />
          </SettingsCard>

          <SettingsCard title="Auditoria e Segurança">
            <ToggleSwitch
              id="require-live-photo"
              label="Apenas Foto Tirada na Hora"
              description="Na comprovação por foto, força o uso da câmera do aparelho em vez de permitir escolher uma imagem já salva."
              checked={requireLivePhotoOnly}
              onChange={setRequireLivePhotoOnly}
            />
            <ToggleSwitch
              id="require-pin-on-complete"
              label="Exigir PIN na Conclusão"
              description={'Pede o PIN de novo ao clicar em "Concluir" ou "Reportar Impedimento", mesmo dentro da mesma sessão.'}
              checked={requirePinOnComplete}
              onChange={setRequirePinOnComplete}
            />
          </SettingsCard>

          {errorMessage && (
            <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
              {errorMessage}
            </p>
          )}
          {savedMessage && !errorMessage && (
            <p className="rounded-lg bg-emerald-50 px-3 py-2 text-sm text-emerald-600">Configurações salvas.</p>
          )}

          <button
            type="submit"
            disabled={isSubmitting}
            className="w-fit rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50"
          >
            Salvar
          </button>
        </form>
      )}
    </div>
  )
}
