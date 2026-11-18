import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { ConfirmDeleteModal } from '../../components/admin/ConfirmDeleteModal'
import { TrashIcon } from '../../components/icons/TrashIcon'
import { getApiErrorMessage } from '../../services/apiClient'
import { deleteSector, listSectors, updateSector } from '../../services/sectorService'
import { listStores } from '../../services/storeService'
import type { Sector } from '../../types/sector'
import { SectorFormModal } from './SectorFormModal'

type FormState = { mode: 'create' } | { mode: 'edit'; sector: Sector } | null

export function SectorsPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<FormState>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [sectorToDelete, setSectorToDelete] = useState<Sector | null>(null)
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null)

  const sectorsQuery = useQuery({ queryKey: ['sectors', 'admin'], queryFn: () => listSectors() })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateSector(id, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['sectors', 'admin'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteSector(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['sectors', 'admin'] })
      setSectorToDelete(null)
      setDeleteErrorMessage(null)
    },
    onError: (error: unknown) => setDeleteErrorMessage(getApiErrorMessage(error)),
  })

  const allSectors = sectorsQuery.data ?? []
  const sectors = showInactive ? allSectors : allSectors.filter((sector) => sector.active)
  const stores = storesQuery.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Setores</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
            />
            Mostrar inativos
          </label>
          <button
            type="button"
            onClick={() => setFormState({ mode: 'create' })}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md"
          >
            Novo Setor
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {sectorsQuery.isLoading && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!sectorsQuery.isLoading && sectors.length === 0 && (
              <tr>
                <td colSpan={3} className="px-4 py-6 text-center text-gray-500">
                  Nenhum setor cadastrado ainda.
                </td>
              </tr>
            )}
            {sectors.map((sector) => (
              <tr key={sector.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{sector.name}</td>
                <td className="px-4 py-3">
                  {sector.active ? (
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                      Ativo
                    </span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                      Inativo
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setFormState({ mode: 'edit', sector })}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleActiveMutation.mutate({ id: sector.id, active: !sector.active })}
                      disabled={toggleActiveMutation.isPending}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {sector.active ? 'Desativar' : 'Ativar'}
                    </button>
                    {isMaster && (
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteErrorMessage(null)
                          setSectorToDelete(sector)
                        }}
                        className="flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                        Excluir
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {formState && (
        <SectorFormModal
          {...(formState.mode === 'create' ? { mode: 'create' } : { mode: 'edit', sector: formState.sector })}
          stores={stores}
          isMaster={isMaster}
          onClose={() => setFormState(null)}
        />
      )}

      {sectorToDelete && (
        <ConfirmDeleteModal
          title="Excluir setor"
          message={
            <>
              Tem certeza que deseja excluir <strong>{sectorToDelete.name}</strong>? Funcionários já vinculados a
              este setor continuam com o vínculo mantido, mas ele some do cadastro e não pode mais ser escolhido.
            </>
          }
          isSubmitting={deleteMutation.isPending}
          errorMessage={deleteErrorMessage}
          onConfirm={() => deleteMutation.mutate(sectorToDelete.id)}
          onClose={() => setSectorToDelete(null)}
        />
      )}
    </div>
  )
}
