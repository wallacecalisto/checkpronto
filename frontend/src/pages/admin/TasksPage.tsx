import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { ConfirmDeleteModal } from '../../components/admin/ConfirmDeleteModal'
import { SearchIcon } from '../../components/icons/SearchIcon'
import { TrashIcon } from '../../components/icons/TrashIcon'
import { getApiErrorMessage } from '../../services/apiClient'
import { listStores } from '../../services/storeService'
import { deleteTask, listTasks, updateTask } from '../../services/taskService'
import type { Task } from '../../types/task'
import { TaskFormModal } from './TaskFormModal'

type FormState = { mode: 'create' } | { mode: 'edit'; task: Task } | null

export function TasksPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<FormState>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [searchTerm, setSearchTerm] = useState('')
  const [taskToDelete, setTaskToDelete] = useState<Task | null>(null)
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null)

  const tasksQuery = useQuery({ queryKey: ['tasks', 'admin'], queryFn: () => listTasks() })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateTask(id, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['tasks', 'admin'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteTask(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', 'admin'] })
      setTaskToDelete(null)
      setDeleteErrorMessage(null)
    },
    onError: (error: unknown) => setDeleteErrorMessage(getApiErrorMessage(error)),
  })

  const allTasks = tasksQuery.data ?? []
  const visibleTasks = showInactive ? allTasks : allTasks.filter((task) => task.active)
  const normalizedSearchTerm = searchTerm.trim().toLowerCase()
  const tasks = normalizedSearchTerm
    ? visibleTasks.filter((task) => task.title.toLowerCase().includes(normalizedSearchTerm))
    : visibleTasks
  const stores = storesQuery.data ?? []

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Catálogo de Tarefas</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
            />
            Mostrar inativas
          </label>
          <button
            type="button"
            onClick={() => setFormState({ mode: 'create' })}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md"
          >
            Nova Tarefa
          </button>
        </div>
      </div>

      <div className="relative sm:w-80">
        <SearchIcon className="pointer-events-none absolute left-3 top-1/2 h-4 w-4 -translate-y-1/2 text-gray-400" />
        <input
          type="text"
          value={searchTerm}
          onChange={(event) => setSearchTerm(event.target.value)}
          placeholder="Buscar tarefa pelo nome…"
          aria-label="Buscar tarefa"
          className="w-full rounded-lg border border-gray-200 bg-gray-50 py-2 pl-9 pr-3 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
        />
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Título</th>
              <th className="px-4 py-3 font-medium">Tempo Estimado</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {tasksQuery.isLoading && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!tasksQuery.isLoading && tasks.length === 0 && (
              <tr>
                <td colSpan={4} className="px-4 py-6 text-center text-gray-500">
                  {normalizedSearchTerm ? 'Nenhuma tarefa encontrada para essa busca.' : 'Nenhuma tarefa cadastrada ainda.'}
                </td>
              </tr>
            )}
            {tasks.map((task) => (
              <tr key={task.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3">
                  <p className="font-medium text-gray-900">{task.title}</p>
                  {task.description && <p className="text-xs text-gray-500">{task.description}</p>}
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {task.estimated_duration_minutes != null ? `${task.estimated_duration_minutes} min` : '—'}
                </td>
                <td className="px-4 py-3">
                  {task.active ? (
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
                      onClick={() => setFormState({ mode: 'edit', task })}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleActiveMutation.mutate({ id: task.id, active: !task.active })}
                      disabled={toggleActiveMutation.isPending}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {task.active ? 'Desativar' : 'Ativar'}
                    </button>
                    {isMaster && (
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteErrorMessage(null)
                          setTaskToDelete(task)
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
        <TaskFormModal
          {...(formState.mode === 'create' ? { mode: 'create' } : { mode: 'edit', task: formState.task })}
          stores={stores}
          isMaster={isMaster}
          onClose={() => setFormState(null)}
        />
      )}

      {taskToDelete && (
        <ConfirmDeleteModal
          title="Excluir tarefa"
          message={
            <>
              Tem certeza que deseja excluir <strong>{taskToDelete.title}</strong>? O histórico de execuções passadas é
              mantido, mas ela some do catálogo e não pode mais ser agendada.
            </>
          }
          isSubmitting={deleteMutation.isPending}
          errorMessage={deleteErrorMessage}
          onConfirm={() => deleteMutation.mutate(taskToDelete.id)}
          onClose={() => setTaskToDelete(null)}
        />
      )}
    </div>
  )
}
