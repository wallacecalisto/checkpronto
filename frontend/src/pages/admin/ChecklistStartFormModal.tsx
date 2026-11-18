import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { useNavigate } from 'react-router-dom'
import { Modal } from '../../components/Modal'
import { SearchableSelect } from '../../components/SearchableSelect'
import { getApiErrorMessage } from '../../services/apiClient'
import { startChecklistExecution } from '../../services/checklistService'
import { SHIFT_LABEL, SHIFTS, suggestedShift, type Shift } from '../../types/checklistExecution'
import type { ChecklistTemplate } from '../../types/checklistTemplate'

interface ChecklistStartFormModalProps {
  templates: ChecklistTemplate[]
  onClose: () => void
}

export function ChecklistStartFormModal({ templates, onClose }: ChecklistStartFormModalProps) {
  const queryClient = useQueryClient()
  const navigate = useNavigate()
  const [templateId, setTemplateId] = useState('')
  const [shift, setShift] = useState<Shift>(suggestedShift())
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const mutation = useMutation({
    mutationFn: () => startChecklistExecution({ template_id: Number(templateId), shift }),
    onSuccess: (execution) => {
      queryClient.invalidateQueries({ queryKey: ['checklists', 'admin'] })
      onClose()
      navigate(`/admin/checklists/${execution.id}`)
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setErrorMessage(null)
    mutation.mutate()
  }

  return (
    <Modal title="Iniciar checklist" onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="start-template" className="text-sm font-medium text-gray-700">
            Checklist
          </label>
          <SearchableSelect
            id="start-template"
            required
            value={templateId}
            onChange={setTemplateId}
            options={templates.map((template) => ({ value: String(template.id), label: template.name }))}
            placeholder="Buscar checklist…"
            emptyLabel="Nenhum checklist encontrado."
          />
          {templates.length === 0 && (
            <p className="text-xs text-gray-400">Nenhum checklist ativo ainda — cadastre um em "Checklists" primeiro.</p>
          )}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="start-shift" className="text-sm font-medium text-gray-700">
            Turno
          </label>
          <select
            id="start-shift"
            value={shift}
            onChange={(event) => setShift(event.target.value as Shift)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            {SHIFTS.map((option) => (
              <option key={option} value={option}>
                {SHIFT_LABEL[option]}
              </option>
            ))}
          </select>
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
            disabled={mutation.isPending || templateId === ''}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            {mutation.isPending ? 'Iniciando…' : 'Iniciar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
