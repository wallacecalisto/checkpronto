import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { SearchableSelect } from '../../components/SearchableSelect'
import { getApiErrorMessage } from '../../services/apiClient'
import { createTaskAssignment, updateTaskAssignment } from '../../services/taskAssignmentService'
import type { Sector } from '../../types/sector'
import type { Task } from '../../types/task'
import { DAY_OF_WEEK_LABEL, DAYS_OF_WEEK, type DayOfWeek, type TaskAssignment } from '../../types/taskAssignment'

const NO_SECTOR = ''

type TaskAssignmentFormModalProps = { sectors: Sector[]; shiftOptions: string[]; onClose: () => void } & (
  | { mode: 'create'; tasks: Task[]; defaultDay: DayOfWeek }
  | { mode: 'edit'; assignment: TaskAssignment }
)

export function TaskAssignmentFormModal(props: TaskAssignmentFormModalProps) {
  const { sectors, shiftOptions, onClose } = props
  const queryClient = useQueryClient()

  const [taskId, setTaskId] = useState(props.mode === 'create' ? '' : String(props.assignment.task_id))
  const [dayOfWeek, setDayOfWeek] = useState<DayOfWeek>(
    props.mode === 'create' ? props.defaultDay : props.assignment.day_of_week,
  )
  const [sectorId, setSectorId] = useState(
    props.mode === 'edit' ? String(props.assignment.sector_id) : NO_SECTOR,
  )
  const [shift, setShift] = useState(props.mode === 'edit' ? props.assignment.shift : (shiftOptions[0] ?? ''))
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const canSubmit = sectorId !== NO_SECTOR && shift !== ''

  const mutation = useMutation({
    mutationFn: async () => {
      if (props.mode === 'edit') {
        return updateTaskAssignment(props.assignment.id, {
          day_of_week: dayOfWeek,
          sector_id: sectorId ? Number(sectorId) : undefined,
          shift: shift || undefined,
        })
      }
      return createTaskAssignment({
        task_id: Number(taskId),
        day_of_week: dayOfWeek,
        sector_id: Number(sectorId),
        shift,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['task-assignments', 'admin'] })
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
    <Modal title={props.mode === 'edit' ? 'Editar agendamento' : 'Novo agendamento'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        {props.mode === 'create' && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="assignment-task" className="text-sm font-medium text-gray-700">
              Tarefa do catálogo
            </label>
            <SearchableSelect
              id="assignment-task"
              required
              value={taskId}
              onChange={(newTaskId) => {
                setTaskId(newTaskId)
                setSectorId(NO_SECTOR)
              }}
              options={props.tasks.map((task) => ({ value: String(task.id), label: task.title }))}
              placeholder="Buscar tarefa…"
              emptyLabel="Nenhuma tarefa encontrada."
            />
            {props.tasks.length === 0 && (
              <p className="text-xs text-gray-400">
                Nenhuma tarefa ativa no catálogo ainda — cadastre uma em "Tarefas" primeiro.
              </p>
            )}
          </div>
        )}

        {props.mode === 'edit' && (
          <div className="flex flex-col gap-1.5">
            <p className="text-sm font-medium text-gray-700">Tarefa</p>
            <p className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-500">
              {props.assignment.task_title}
            </p>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="assignment-shift" className="text-sm font-medium text-gray-700">
            Turno
          </label>
          <select
            id="assignment-shift"
            required
            value={shift}
            onChange={(event) => setShift(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="" disabled>
              Selecione…
            </option>
            {shiftOptions.map((shiftOption) => (
              <option key={shiftOption} value={shiftOption}>
                {shiftOption}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="assignment-day" className="text-sm font-medium text-gray-700">
            Dia da semana
          </label>
          <select
            id="assignment-day"
            value={dayOfWeek}
            onChange={(event) => setDayOfWeek(event.target.value as DayOfWeek)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            {DAYS_OF_WEEK.map((day) => (
              <option key={day} value={day}>
                {DAY_OF_WEEK_LABEL[day]}
              </option>
            ))}
          </select>
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="assignment-sector" className="text-sm font-medium text-gray-700">
            Setor
          </label>
          <select
            id="assignment-sector"
            required
            value={sectorId}
            onChange={(event) => setSectorId(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value={NO_SECTOR} disabled>
              Selecione…
            </option>
            {sectors.map((sector) => (
              <option key={sector.id} value={sector.id}>
                {sector.name}
              </option>
            ))}
          </select>
          {sectors.length === 0 && (
            <p className="text-xs text-gray-400">Nenhum setor ativo nesta loja ainda.</p>
          )}
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
            disabled={mutation.isPending || (props.mode === 'create' && taskId === '') || !canSubmit}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            {mutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
