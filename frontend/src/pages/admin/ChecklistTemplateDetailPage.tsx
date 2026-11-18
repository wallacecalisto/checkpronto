import { useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { getApiErrorMessage } from '../../services/apiClient'
import {
  createChecklistTemplateItem,
  getChecklistTemplate,
  updateChecklistTemplateItem,
} from '../../services/checklistTemplateService'
import type { ChecklistTemplateItem } from '../../types/checklistTemplate'

export function ChecklistTemplateDetailPage() {
  const params = useParams<{ id: string }>()
  const templateId = Number(params.id)
  const queryClient = useQueryClient()

  const [newDescription, setNewDescription] = useState('')
  const [newRequired, setNewRequired] = useState(true)
  const [newRequiresPhoto, setNewRequiresPhoto] = useState(false)
  const [editingItem, setEditingItem] = useState<ChecklistTemplateItem | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const templateQuery = useQuery({
    queryKey: ['checklist-templates', 'admin', templateId],
    queryFn: () => getChecklistTemplate(templateId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['checklist-templates', 'admin', templateId] })
    queryClient.invalidateQueries({ queryKey: ['checklist-templates', 'admin'] })
  }

  const addItemMutation = useMutation({
    mutationFn: () =>
      createChecklistTemplateItem(templateId, {
        description: newDescription.trim(),
        order_index: (templateQuery.data?.items.length ?? 0) + 1,
        required: newRequired,
        requires_photo: newRequiresPhoto,
      }),
    onSuccess: () => {
      setNewDescription('')
      setNewRequired(true)
      setNewRequiresPhoto(false)
      invalidate()
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  const editItemMutation = useMutation({
    mutationFn: (payload: { description: string; required: boolean; requires_photo: boolean }) =>
      updateChecklistTemplateItem(editingItem!.id, payload),
    onSuccess: () => {
      setEditingItem(null)
      invalidate()
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateChecklistTemplateItem(id, { active }),
    onSuccess: invalidate,
  })

  function handleAddItem(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setErrorMessage(null)
    addItemMutation.mutate()
  }

  function handleEditSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    if (!editingItem) return
    setErrorMessage(null)
    editItemMutation.mutate({
      description: editingItem.description,
      required: editingItem.required,
      requires_photo: editingItem.requires_photo,
    })
  }

  const template = templateQuery.data
  const items = [...(template?.items ?? [])].sort((a, b) => a.order_index - b.order_index)

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/admin/checklist-templates" className="text-sm text-emerald-600 hover:underline">
          ← Voltar para Checklists
        </Link>
        <h1 className="mt-1 text-xl font-semibold text-gray-900">
          {templateQuery.isLoading ? 'Carregando…' : (template?.name ?? 'Checklist')}
        </h1>
      </div>

      {errorMessage && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {errorMessage}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Descrição</th>
              <th className="px-4 py-3 font-medium">Obrigatório</th>
              <th className="px-4 py-3 font-medium">Foto</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {!templateQuery.isLoading && items.length === 0 && (
              <tr>
                <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                  Nenhum item cadastrado ainda.
                </td>
              </tr>
            )}
            {items.map((item) =>
              editingItem?.id === item.id ? (
                <tr key={item.id} className="border-b border-gray-100 last:border-0 bg-gray-50">
                  <td className="px-4 py-3" colSpan={5}>
                    <form onSubmit={handleEditSubmit} className="flex flex-wrap items-center gap-2">
                      <input
                        required
                        value={editingItem.description}
                        onChange={(event) => setEditingItem({ ...editingItem, description: event.target.value })}
                        className="min-w-[16rem] flex-1 rounded-lg border border-gray-200 bg-white px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                      />
                      <label className="flex items-center gap-1.5 text-xs text-gray-600">
                        <input
                          type="checkbox"
                          checked={editingItem.required}
                          onChange={(event) => setEditingItem({ ...editingItem, required: event.target.checked })}
                          className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
                        />
                        Obrigatório
                      </label>
                      <label className="flex items-center gap-1.5 text-xs text-gray-600">
                        <input
                          type="checkbox"
                          checked={editingItem.requires_photo}
                          onChange={(event) => setEditingItem({ ...editingItem, requires_photo: event.target.checked })}
                          className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
                        />
                        Exige foto
                      </label>
                      <button
                        type="submit"
                        disabled={editItemMutation.isPending}
                        className="rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-60"
                      >
                        Salvar
                      </button>
                      <button
                        type="button"
                        onClick={() => setEditingItem(null)}
                        className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                      >
                        Cancelar
                      </button>
                    </form>
                  </td>
                </tr>
              ) : (
                <tr key={item.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 text-gray-900">{item.description}</td>
                  <td className="px-4 py-3 text-gray-600">{item.required ? 'Sim' : 'Não'}</td>
                  <td className="px-4 py-3 text-gray-600">{item.requires_photo ? 'Sim' : 'Não'}</td>
                  <td className="px-4 py-3">
                    {item.active ? (
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
                        onClick={() => setEditingItem(item)}
                        className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => toggleActiveMutation.mutate({ id: item.id, active: !item.active })}
                        disabled={toggleActiveMutation.isPending}
                        className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        {item.active ? 'Desativar' : 'Ativar'}
                      </button>
                    </div>
                  </td>
                </tr>
              ),
            )}
          </tbody>
        </table>
      </div>

      <form onSubmit={handleAddItem} className="flex flex-wrap items-end gap-3 rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
        <div className="flex min-w-[16rem] flex-1 flex-col gap-1.5">
          <label htmlFor="new-item-description" className="text-sm font-medium text-gray-700">
            Novo item
          </label>
          <input
            id="new-item-description"
            required
            value={newDescription}
            onChange={(event) => setNewDescription(event.target.value)}
            placeholder="Ex.: Trancar a porta dos fundos"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>
        <label className="flex items-center gap-1.5 pb-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={newRequired}
            onChange={(event) => setNewRequired(event.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
          />
          Obrigatório
        </label>
        <label className="flex items-center gap-1.5 pb-2 text-sm text-gray-600">
          <input
            type="checkbox"
            checked={newRequiresPhoto}
            onChange={(event) => setNewRequiresPhoto(event.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
          />
          Exige foto
        </label>
        <button
          type="submit"
          disabled={addItemMutation.isPending}
          className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
        >
          {addItemMutation.isPending ? 'Adicionando…' : 'Adicionar'}
        </button>
      </form>
    </div>
  )
}
