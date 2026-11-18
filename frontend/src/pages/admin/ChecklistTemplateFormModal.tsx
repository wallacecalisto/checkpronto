import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { Modal } from '../../components/Modal'
import { getApiErrorMessage } from '../../services/apiClient'
import { createChecklistTemplate, updateChecklistTemplate } from '../../services/checklistTemplateService'
import { listSectors } from '../../services/sectorService'
import { getStoreSettings } from '../../services/storeSettingsService'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import type { Store } from '../../types/store'

const NO_SECTOR = ''
const SHIFT_NOT_LOADED_YET = ''

type ChecklistTemplateFormModalProps = { stores: Store[]; isMaster: boolean; onClose: () => void } & (
  | { mode: 'create' }
  | { mode: 'edit'; template: ChecklistTemplate }
)

interface DraftItem {
  key: number
  description: string
  required: boolean
  requiresPhoto: boolean
}

export function ChecklistTemplateFormModal(props: ChecklistTemplateFormModalProps) {
  const { stores, isMaster, onClose } = props
  const existingTemplate = props.mode === 'edit' ? props.template : null
  const { user } = useAuth()

  const queryClient = useQueryClient()
  const [name, setName] = useState(existingTemplate?.name ?? '')
  const [storeId, setStoreId] = useState('')
  const [targetSectorId, setTargetSectorId] = useState(
    existingTemplate?.target_sector_id ? String(existingTemplate.target_sector_id) : NO_SECTOR,
  )
  const [shift, setShift] = useState(existingTemplate?.shift ?? SHIFT_NOT_LOADED_YET)
  const [draftItems, setDraftItems] = useState<DraftItem[]>(
    existingTemplate ? [] : [{ key: 0, description: '', required: true, requiresPhoto: false }],
  )
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const templateStoreId = existingTemplate
    ? existingTemplate.store_id
    : isMaster
      ? storeId
        ? Number(storeId)
        : undefined
      : (user?.store_id ?? undefined)
  const sectorsQuery = useQuery({
    queryKey: ['sectors', 'for-checklist-template', templateStoreId],
    queryFn: () => listSectors({ activeOnly: true, storeId: templateStoreId }),
    enabled: templateStoreId !== undefined,
  })
  const sectors = sectorsQuery.data ?? []
  const storeSettingsQuery = useQuery({
    queryKey: ['store-settings', 'for-checklist-template', templateStoreId],
    queryFn: () => getStoreSettings(templateStoreId as number),
    enabled: templateStoreId !== undefined,
  })
  const shiftOptions = storeSettingsQuery.data?.shifts ?? []

  useEffect(() => {
    if (!shift && shiftOptions.length > 0) {
      setShift(shiftOptions[0])
    }
  }, [shift, shiftOptions])

  const mutation = useMutation({
    mutationFn: async () => {
      const resolvedTargetSectorId = targetSectorId ? Number(targetSectorId) : null
      if (existingTemplate) {
        return updateChecklistTemplate(existingTemplate.id, {
          name,
          target_sector_id: resolvedTargetSectorId,
          shift,
        })
      }
      return createChecklistTemplate({
        name,
        store_id: isMaster ? Number(storeId) : undefined,
        target_sector_id: resolvedTargetSectorId ?? undefined,
        shift,
        items: draftItems
          .filter((item) => item.description.trim().length > 0)
          .map((item, index) => ({
            description: item.description.trim(),
            order_index: index,
            required: item.required,
            requires_photo: item.requiresPhoto,
          })),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['checklist-templates'] })
      onClose()
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setErrorMessage(null)
    mutation.mutate()
  }

  function addDraftItem(): void {
    setDraftItems((current) => [
      ...current,
      { key: Date.now(), description: '', required: true, requiresPhoto: false },
    ])
  }

  function removeDraftItem(key: number): void {
    setDraftItems((current) => current.filter((item) => item.key !== key))
  }

  function updateDraftItem(key: number, changes: Partial<DraftItem>): void {
    setDraftItems((current) => current.map((item) => (item.key === key ? { ...item, ...changes } : item)))
  }

  const hasAtLeastOneItem = existingTemplate || draftItems.some((item) => item.description.trim().length > 0)

  return (
    <Modal title={existingTemplate ? 'Editar checklist' : 'Novo checklist'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="checklist-name" className="text-sm font-medium text-gray-700">
            Nome
          </label>
          <input
            id="checklist-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ex.: Fechamento da cozinha"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        {!existingTemplate && isMaster && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="checklist-store" className="text-sm font-medium text-gray-700">
              Loja
            </label>
            <select
              id="checklist-store"
              required
              value={storeId}
              onChange={(event) => setStoreId(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="" disabled>
                Selecione…
              </option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="checklist-sector" className="text-sm font-medium text-gray-700">
            Setor
          </label>
          <select
            id="checklist-sector"
            value={targetSectorId}
            onChange={(event) => setTargetSectorId(event.target.value)}
            disabled={isMaster && !existingTemplate && storeId === ''}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <option value={NO_SECTOR}>Nenhum (checklist de gestão)</option>
            {sectors.map((sector) => (
              <option key={sector.id} value={sector.id}>
                {sector.name}
              </option>
            ))}
          </select>
          <p className="text-xs text-gray-400">
            Preenchido, este checklist também aparece para funcionários do setor no tablet (via PIN).
          </p>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="checklist-shift" className="text-sm font-medium text-gray-700">
            Turno
          </label>
          <select
            id="checklist-shift"
            required
            value={shift}
            onChange={(event) => setShift(event.target.value)}
            disabled={templateStoreId === undefined}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            {shiftOptions.map((shiftOption) => (
              <option key={shiftOption} value={shiftOption}>
                {shiftOption}
              </option>
            ))}
          </select>
        </div>

        {!existingTemplate && (
          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-gray-700">Itens</p>
            {draftItems.map((item) => (
              <div key={item.key} className="flex items-center gap-2">
                <input
                  value={item.description}
                  onChange={(event) => updateDraftItem(item.key, { description: event.target.value })}
                  placeholder="Ex.: Desligar a fritadeira"
                  className="flex-1 rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                />
                <label className="flex shrink-0 items-center gap-1.5 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={item.required}
                    onChange={(event) => updateDraftItem(item.key, { required: event.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
                  />
                  Obrigatório
                </label>
                <label className="flex shrink-0 items-center gap-1.5 text-xs text-gray-600">
                  <input
                    type="checkbox"
                    checked={item.requiresPhoto}
                    onChange={(event) => updateDraftItem(item.key, { requiresPhoto: event.target.checked })}
                    className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
                  />
                  Exige foto
                </label>
                <button
                  type="button"
                  onClick={() => removeDraftItem(item.key)}
                  aria-label="Remover item"
                  className="shrink-0 rounded-lg p-2 text-gray-400 transition hover:bg-gray-100 hover:text-red-600"
                >
                  ✕
                </button>
              </div>
            ))}
            <button
              type="button"
              onClick={addDraftItem}
              className="self-start rounded-lg border border-dashed border-gray-300 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
            >
              + Adicionar item
            </button>
          </div>
        )}

        {errorMessage && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {errorMessage}
          </p>
        )}

        <div className="mt-2 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={mutation.isPending || !hasAtLeastOneItem}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            {mutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
