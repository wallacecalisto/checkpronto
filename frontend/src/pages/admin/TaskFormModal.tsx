import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { getApiErrorMessage } from '../../services/apiClient'
import { createTask, updateTask } from '../../services/taskService'
import type { Store } from '../../types/store'
import type { Task } from '../../types/task'

// Cadastro do CATÁLOGO — só a definição reutilizável (title/description).
// Dia da semana e funcionário são do agendamento, ver TaskAssignmentFormModal.
type TaskFormModalProps = { stores: Store[]; isMaster: boolean; onClose: () => void } & (
  | { mode: 'create' }
  | { mode: 'edit'; task: Task }
)

export function TaskFormModal(props: TaskFormModalProps) {
  const { stores, isMaster, onClose } = props
  const existingTask = props.mode === 'edit' ? props.task : null

  const queryClient = useQueryClient()
  const [title, setTitle] = useState(existingTask?.title ?? '')
  const [description, setDescription] = useState(existingTask?.description ?? '')
  const [estimatedDuration, setEstimatedDuration] = useState(
    existingTask?.estimated_duration_minutes != null ? String(existingTask.estimated_duration_minutes) : '',
  )
  const [storeId, setStoreId] = useState('')
  const [requiresPhotoProof, setRequiresPhotoProof] = useState(existingTask?.requires_photo_proof ?? false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: async () => {
      if (existingTask) {
        return updateTask(existingTask.id, {
          title,
          description: description || undefined,
          estimated_duration_minutes: estimatedDuration ? Number(estimatedDuration) : null,
          requires_photo_proof: requiresPhotoProof,
        })
      }
      return createTask({
        title,
        description: description || undefined,
        estimated_duration_minutes: estimatedDuration ? Number(estimatedDuration) : undefined,
        requires_photo_proof: requiresPhotoProof,
        store_id: isMaster ? Number(storeId) : undefined,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['tasks', 'admin'] })
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
    <Modal title={existingTask ? 'Editar tarefa' : 'Nova tarefa'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="task-title" className="text-sm font-medium text-gray-700">
            Título
          </label>
          <input
            id="task-title"
            required
            value={title}
            onChange={(event) => setTitle(event.target.value)}
            placeholder="Ex.: Fazer 150 filadélfias"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="task-description" className="text-sm font-medium text-gray-700">
            Descrição (opcional)
          </label>
          <textarea
            id="task-description"
            rows={3}
            value={description}
            onChange={(event) => setDescription(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="task-estimated-duration" className="text-sm font-medium text-gray-700">
            Tempo Estimado (minutos) — opcional
          </label>
          <input
            id="task-estimated-duration"
            type="number"
            min={1}
            step={1}
            value={estimatedDuration}
            onChange={(event) => setEstimatedDuration(event.target.value)}
            placeholder="Ex.: 30"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
          <p className="text-xs text-gray-400">
            Se preenchido, uma execução mais longa que isso conta como "com atraso" nos relatórios.
          </p>
        </div>

        <label className="flex items-center gap-2 text-sm text-gray-700">
          <input
            type="checkbox"
            checked={requiresPhotoProof}
            onChange={(event) => setRequiresPhotoProof(event.target.checked)}
            className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
          />
          Exige foto para concluir como "Feito"
        </label>

        {!existingTask && isMaster && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="task-store" className="text-sm font-medium text-gray-700">
              Loja
            </label>
            <select
              id="task-store"
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
