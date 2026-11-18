import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { listStores, updateStore } from '../../services/storeService'
import type { Store } from '../../types/store'
import { StoreFormModal } from './StoreFormModal'

// Exclusiva do MASTER (rota gateada em routes/AppRoutes.tsx) — CRUD de lojas.
type FormState = { mode: 'create' } | { mode: 'edit'; store: Store } | null

export function StoresPage() {
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<FormState>(null)

  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateStore(id, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['stores'] }),
  })

  const stores = storesQuery.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex items-center justify-between">
        <h1 className="text-xl font-semibold text-gray-900">Lojas</h1>
        <button
          type="button"
          onClick={() => setFormState({ mode: 'create' })}
          className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md"
        >
          Nova Loja
        </button>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">Marca</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {storesQuery.isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!storesQuery.isLoading && stores.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  Nenhuma loja cadastrada.
                </td>
              </tr>
            )}
            {stores.map((store) => (
              <tr key={store.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{store.name}</td>
                <td className="px-4 py-3 text-gray-600">{store.brand ?? '—'}</td>
                <td className="px-4 py-3">
                  {store.active ? (
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                      Ativa
                    </span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                      Inativa
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setFormState({ mode: 'edit', store })}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleActiveMutation.mutate({ id: store.id, active: !store.active })}
                      disabled={toggleActiveMutation.isPending}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {store.active ? 'Desativar' : 'Ativar'}
                    </button>
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {formState && (
        <StoreFormModal
          {...(formState.mode === 'create' ? { mode: 'create' } : { mode: 'edit', store: formState.store })}
          onClose={() => setFormState(null)}
        />
      )}
    </div>
  )
}
