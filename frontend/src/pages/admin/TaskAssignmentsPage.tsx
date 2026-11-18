import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { getApiErrorMessage } from '../../services/apiClient'
import { listSectors } from '../../services/sectorService'
import { getStoreSettings } from '../../services/storeSettingsService'
import { listStores } from '../../services/storeService'
import { listTasks } from '../../services/taskService'
import { deleteTaskAssignment, listTaskAssignments } from '../../services/taskAssignmentService'
import {
  DAY_OF_WEEK_LABEL,
  DAYS_OF_WEEK,
  currentDayOfWeek,
  type DayOfWeek,
  type TaskAssignment,
} from '../../types/taskAssignment'
import { ExecutionTimelineModal } from './ExecutionTimelineModal'
import { TaskAssignmentFormModal } from './TaskAssignmentFormModal'

const STATUS_LABEL: Record<string, string> = {
  PENDING: 'Pendente',
  IN_PROGRESS: 'Em andamento',
  COMPLETED: 'Concluída',
  BLOCKED: 'Impedida',
}

const STATUS_BADGE: Record<string, string> = {
  PENDING: 'bg-gray-100 text-gray-600',
  IN_PROGRESS: 'bg-emerald-50 text-emerald-600',
  COMPLETED: 'bg-blue-50 text-blue-600',
  BLOCKED: 'bg-amber-50 text-amber-600',
}

type FormState = { mode: 'create' } | { mode: 'edit'; assignment: TaskAssignment } | null

export function TaskAssignmentsPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const queryClient = useQueryClient()

  const [storeId, setStoreId] = useState('')
  const [selectedDay, setSelectedDay] = useState<DayOfWeek>(currentDayOfWeek())
  const [sectorFilter, setSectorFilter] = useState('')
  const [shiftFilter, setShiftFilter] = useState('')
  const [formState, setFormState] = useState<FormState>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [timelineHistoryId, setTimelineHistoryId] = useState<number | null>(null)

  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })
  const stores = storesQuery.data ?? []
  const hasStoreContext = !isMaster || storeId !== ''
  const effectiveStoreId = isMaster && storeId ? Number(storeId) : undefined
  const effectiveSectorId = sectorFilter ? Number(sectorFilter) : undefined

  const shiftsStoreId = isMaster ? effectiveStoreId : (user?.store_id ?? undefined)
  const storeSettingsQuery = useQuery({
    queryKey: ['store-settings', 'for-assignments', shiftsStoreId],
    queryFn: () => getStoreSettings(shiftsStoreId as number),
    enabled: shiftsStoreId !== undefined,
  })
  const shiftOptions = storeSettingsQuery.data?.shifts ?? []

  const assignmentsQuery = useQuery({
    queryKey: ['task-assignments', 'admin', selectedDay, effectiveStoreId, effectiveSectorId, shiftFilter],
    queryFn: () =>
      listTaskAssignments({
        dayOfWeek: selectedDay,
        storeId: effectiveStoreId,
        sectorId: effectiveSectorId,
        shift: shiftFilter || undefined,
      }),
    enabled: hasStoreContext,
  })

  const tasksQuery = useQuery({
    queryKey: ['tasks', 'for-assignments', effectiveStoreId],
    queryFn: () => listTasks({ activeOnly: true, storeId: effectiveStoreId }),
    enabled: hasStoreContext,
  })

  // Só setores ativos — igual ao resto do admin (não faz sentido agendar
  // pra um setor que nem existe mais no tablet).
  const sectorsQuery = useQuery({
    queryKey: ['sectors', 'for-assignments', effectiveStoreId],
    queryFn: () => listSectors({ activeOnly: true, storeId: effectiveStoreId }),
    enabled: hasStoreContext,
  })

  const deleteMutation = useMutation({
    mutationFn: (assignmentId: number) => deleteTaskAssignment(assignmentId),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['task-assignments', 'admin'] }),
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  const assignments = assignmentsQuery.data ?? []
  const tasks = tasksQuery.data ?? []
  const sectors = sectorsQuery.data ?? []

  function handleDelete(assignment: TaskAssignment): void {
    const confirmed = window.confirm(
      `Excluir o agendamento "${assignment.task_title}" de ${DAY_OF_WEEK_LABEL[assignment.day_of_week]}?`,
    )
    if (!confirmed) return
    setErrorMessage(null)
    deleteMutation.mutate(assignment.id)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Agendamentos</h1>
        <button
          type="button"
          onClick={() => setFormState({ mode: 'create' })}
          disabled={!hasStoreContext}
          className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
        >
          Novo Agendamento
        </button>
      </div>

      <div className="flex flex-wrap gap-4">
        {isMaster && (
          <div className="flex flex-col gap-1.5 sm:w-64">
            <label htmlFor="assignments-store" className="text-sm font-medium text-gray-700">
              Loja
            </label>
            <select
              id="assignments-store"
              value={storeId}
              onChange={(event) => {
                setStoreId(event.target.value)
                setSectorFilter('')
                setShiftFilter('')
              }}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="" disabled>
                Selecione uma loja…
              </option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {hasStoreContext && (
          <div className="flex flex-col gap-1.5 sm:w-64">
            <label htmlFor="assignments-sector-filter" className="text-sm font-medium text-gray-700">
              Filtrar por setor
            </label>
            <select
              id="assignments-sector-filter"
              value={sectorFilter}
              onChange={(event) => setSectorFilter(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">Todos os setores</option>
              {sectors.map((sector) => (
                <option key={sector.id} value={sector.id}>
                  {sector.name}
                </option>
              ))}
            </select>
          </div>
        )}

        {hasStoreContext && (
          <div className="flex flex-col gap-1.5 sm:w-64">
            <label htmlFor="assignments-shift-filter" className="text-sm font-medium text-gray-700">
              Filtrar por turno
            </label>
            <select
              id="assignments-shift-filter"
              value={shiftFilter}
              onChange={(event) => setShiftFilter(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">Todos os turnos</option>
              {shiftOptions.map((shiftOption) => (
                <option key={shiftOption} value={shiftOption}>
                  {shiftOption}
                </option>
              ))}
            </select>
          </div>
        )}
      </div>

      <div className="flex flex-wrap gap-2">
        {DAYS_OF_WEEK.map((day) => (
          <button
            key={day}
            type="button"
            onClick={() => setSelectedDay(day)}
            className={`rounded-full px-4 py-2 text-sm font-medium transition ${
              selectedDay === day
                ? 'bg-emerald-500 text-white'
                : 'border border-gray-200 bg-white text-gray-600 hover:bg-gray-100'
            }`}
          >
            {DAY_OF_WEEK_LABEL[day]}
          </button>
        ))}
      </div>

      {errorMessage && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {errorMessage}
        </p>
      )}

      {!hasStoreContext ? (
        <div className="rounded-xl border border-gray-200 bg-white p-6 text-center text-gray-500 shadow-sm">
          Selecione uma loja para ver os agendamentos.
        </div>
      ) : (
        <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
          <table className="w-full text-left text-sm">
            <thead className="border-b border-gray-200 text-gray-500">
              <tr>
                <th className="px-4 py-3 font-medium">Tarefa</th>
                <th className="px-4 py-3 font-medium">Setor</th>
                <th className="px-4 py-3 font-medium">Turno</th>
                <th className="px-4 py-3 font-medium">Status</th>
                <th className="px-4 py-3 font-medium">Ações</th>
              </tr>
            </thead>
            <tbody>
              {assignmentsQuery.isLoading && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                    Carregando…
                  </td>
                </tr>
              )}
              {!assignmentsQuery.isLoading && assignments.length === 0 && (
                <tr>
                  <td colSpan={5} className="px-4 py-6 text-center text-gray-500">
                    Nenhum agendamento para {DAY_OF_WEEK_LABEL[selectedDay]}.
                  </td>
                </tr>
              )}
              {assignments.map((assignment) => (
                <tr key={assignment.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                  <td className="px-4 py-3 font-medium text-gray-900">{assignment.task_title}</td>
                  <td className="px-4 py-3 text-gray-600">{assignment.sector_name}</td>
                  <td className="px-4 py-3 text-gray-600">{assignment.shift}</td>
                  <td className="px-4 py-3">
                    <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_BADGE[assignment.status]}`}>
                      {STATUS_LABEL[assignment.status]}
                    </span>
                  </td>
                  <td className="px-4 py-3">
                    <div className="flex gap-2">
                      <button
                        type="button"
                        onClick={() => setFormState({ mode: 'edit', assignment })}
                        className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                      >
                        Editar
                      </button>
                      <button
                        type="button"
                        onClick={() => handleDelete(assignment)}
                        disabled={deleteMutation.isPending}
                        className="rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Excluir
                      </button>
                      {assignment.latest_execution_history_id !== null && (
                        <button
                          type="button"
                          onClick={() => setTimelineHistoryId(assignment.latest_execution_history_id)}
                          className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                        >
                          Ver detalhes
                        </button>
                      )}
                    </div>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        </div>
      )}

      {formState && (
        <TaskAssignmentFormModal
          {...(formState.mode === 'create'
            ? { mode: 'create', tasks, defaultDay: selectedDay }
            : { mode: 'edit', assignment: formState.assignment })}
          sectors={sectors}
          shiftOptions={shiftOptions}
          onClose={() => setFormState(null)}
        />
      )}

      {timelineHistoryId !== null && (
        <ExecutionTimelineModal historyId={timelineHistoryId} onClose={() => setTimelineHistoryId(null)} />
      )}
    </div>
  )
}
