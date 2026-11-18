import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/useAuth'
import { ConfirmDeleteModal } from '../../components/admin/ConfirmDeleteModal'
import { TrashIcon } from '../../components/icons/TrashIcon'
import { getApiErrorMessage } from '../../services/apiClient'
import { listStores } from '../../services/storeService'
import {
  deleteChecklistTemplate,
  listChecklistTemplates,
  updateChecklistTemplate,
} from '../../services/checklistTemplateService'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import { ChecklistTemplateFormModal } from './ChecklistTemplateFormModal'

type FormState = { mode: 'create' } | { mode: 'edit'; template: ChecklistTemplate } | null

export function ChecklistTemplatesPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<FormState>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [templateToDelete, setTemplateToDelete] = useState<ChecklistTemplate | null>(null)
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null)

  const templatesQuery = useQuery({ queryKey: ['checklist-templates', 'admin'], queryFn: () => listChecklistTemplates() })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateChecklistTemplate(id, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['checklist-templates', 'admin'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteChecklistTemplate(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['checklist-templates', 'admin'] })
      setTemplateToDelete(null)
      setDeleteErrorMessage(null)
    },
    onError: (error: unknown) => setDeleteErrorMessage(getApiErrorMessage(error)),
  })

  const allTemplates = templatesQuery.data ?? []
  const templates = showInactive ? allTemplates : allTemplates.filter((template) => template.active)
  const stores = storesQuery.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Checklists</h1>
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
            Novo Checklist
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">Itens</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {templatesQuery.isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!templatesQuery.isLoading && templates.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  Nenhum checklist cadastrado ainda.
                </td>
              </tr>
            )}
            {templates.map((template) => (
              <tr key={template.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{template.name}</td>
                <td className="px-4 py-3 text-gray-600">
                  {template.items.filter((item) => item.active).length} ativo(s)
                </td>
                <td className="px-4 py-3">
                  {template.active ? (
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
                  <div className="flex flex-wrap gap-2">
                    <Link
                      to={`/admin/checklist-templates/${template.id}`}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Gerenciar itens
                    </Link>
                    <button
                      type="button"
                      onClick={() => setFormState({ mode: 'edit', template })}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleActiveMutation.mutate({ id: template.id, active: !template.active })}
                      disabled={toggleActiveMutation.isPending}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {template.active ? 'Desativar' : 'Ativar'}
                    </button>
                    {isMaster && (
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteErrorMessage(null)
                          setTemplateToDelete(template)
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
        <ChecklistTemplateFormModal
          {...(formState.mode === 'create' ? { mode: 'create' } : { mode: 'edit', template: formState.template })}
          stores={stores}
          isMaster={isMaster}
          onClose={() => setFormState(null)}
        />
      )}

      {templateToDelete && (
        <ConfirmDeleteModal
          title="Excluir checklist"
          message={
            <>
              Tem certeza que deseja excluir <strong>{templateToDelete.name}</strong>? O histórico de execuções
              passadas é mantido, mas ele some do catálogo e não pode mais ser iniciado.
            </>
          }
          isSubmitting={deleteMutation.isPending}
          errorMessage={deleteErrorMessage}
          onConfirm={() => deleteMutation.mutate(templateToDelete.id)}
          onClose={() => setTemplateToDelete(null)}
        />
      )}
    </div>
  )
}
