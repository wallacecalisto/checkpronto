import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { getApiErrorMessage } from '../../services/apiClient'
import { createStore, updateStore } from '../../services/storeService'
import type { Store } from '../../types/store'

type StoreFormModalProps = { onClose: () => void } & ({ mode: 'create' } | { mode: 'edit'; store: Store })

export function StoreFormModal(props: StoreFormModalProps) {
  const { onClose } = props
  const existingStore = props.mode === 'edit' ? props.store : null

  const queryClient = useQueryClient()
  const [name, setName] = useState(existingStore?.name ?? '')
  const [brand, setBrand] = useState(existingStore?.brand ?? '')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      if (existingStore) {
        return updateStore(existingStore.id, { name, brand: brand || null })
      }
      return createStore({ name, brand: brand || undefined })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['stores'] })
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
    <Modal title={existingStore ? 'Editar loja' : 'Nova loja'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="store-name" className="text-sm font-medium text-gray-700">
            Nome
          </label>
          <input
            id="store-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="store-brand" className="text-sm font-medium text-gray-700">
            Marca/Bandeira (opcional)
          </label>
          <input
            id="store-brand"
            value={brand}
            onChange={(event) => setBrand(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

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
