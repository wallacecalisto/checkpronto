import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { getApiErrorMessage } from '../../services/apiClient'
import { createSector, updateSector } from '../../services/sectorService'
import type { Sector } from '../../types/sector'
import type { Store } from '../../types/store'

type SectorFormModalProps = { stores: Store[]; isMaster: boolean; onClose: () => void } & (
  | { mode: 'create' }
  | { mode: 'edit'; sector: Sector }
)

export function SectorFormModal(props: SectorFormModalProps) {
  const { stores, isMaster, onClose } = props
  const existingSector = props.mode === 'edit' ? props.sector : null

  const queryClient = useQueryClient()
  const [name, setName] = useState(existingSector?.name ?? '')
  const [storeId, setStoreId] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      if (existingSector) {
        return updateSector(existingSector.id, { name })
      }
      return createSector({ name, store_id: isMaster ? Number(storeId) : undefined })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sectors', 'admin'] })
      onClose()
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setErrorMessage(null)
    mutation.mutate()
  }

  return (
    <Modal title={existingSector ? 'Editar setor' : 'Novo setor'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="sector-name" className="text-sm font-medium text-gray-700">
            Nome
          </label>
          <input
            id="sector-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            placeholder="Ex.: Cozinha Quente"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        {!existingSector && isMaster && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="sector-store" className="text-sm font-medium text-gray-700">
              Loja
            </label>
            <select
              id="sector-store"
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
            disabled={mutation.isPending}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            {mutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
