import { useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Link } from 'react-router-dom'
import { useAuth } from '../../auth/useAuth'
import { DateRangePresetFilter } from '../../components/admin/DateRangePresetFilter'
import { useDateRangeFilter } from '../../hooks/useDateRangeFilter'
import { listChecklistTemplates } from '../../services/checklistTemplateService'
import { listChecklistExecutions } from '../../services/checklistService'
import { SHIFT_LABEL } from '../../types/checklistExecution'
import { formatDateBR } from '../../utils/dateTime'
import { ChecklistStartFormModal } from './ChecklistStartFormModal'

const STATUS_LABEL: Record<string, string> = {
  IN_PROGRESS: 'Em andamento',
  COMPLETED: 'Concluído',
}

const STATUS_BADGE: Record<string, string> = {
  IN_PROGRESS: 'bg-emerald-50 text-emerald-600',
  COMPLETED: 'bg-blue-50 text-blue-600',
}

export function ChecklistsPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const [isStartModalOpen, setIsStartModalOpen] = useState(false)

  const dateRange = useDateRangeFilter('7dias')

  const templatesQuery = useQuery({
    queryKey: ['checklist-templates', 'for-start'],
    queryFn: () => listChecklistTemplates({ activeOnly: true }),
  })
  const executionsQuery = useQuery({
    queryKey: ['checklists', 'admin', dateRange.from, dateRange.to],
    queryFn: () => listChecklistExecutions({ startedFrom: dateRange.from, startedTo: dateRange.to }),
    refetchInterval: 15000,
  })

  const templates = templatesQuery.data ?? []
  const executions = executionsQuery.data ?? []
  const pendingValidation = executions.filter((execution) => execution.status === 'COMPLETED' && !execution.fully_validated)

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Checklists de Turno</h1>
        <div className="flex items-center gap-2">
          {isMaster && (
            <Link
              to="/admin/checklist-templates"
              className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
            >
              Gerenciar catálogo
            </Link>
          )}
          <button
            type="button"
            onClick={() => setIsStartModalOpen(true)}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md"
          >
            Iniciar Checklist
          </button>
        </div>
      </div>

      <DateRangePresetFilter
        preset={dateRange.preset}
        onPresetChange={dateRange.selectPreset}
        customFrom={dateRange.customFrom}
        customTo={dateRange.customTo}
        onCustomFromChange={dateRange.setCustomFrom}
        onCustomToChange={dateRange.setCustomTo}
      />

      {pendingValidation.length > 0 && (
        <div className="rounded-xl border border-orange-200 bg-orange-50 p-4">
          <p className="font-semibold text-orange-800">
            {pendingValidation.length} checklist(s) aguardando validação cruzada
          </p>
          <div className="mt-2 flex flex-col gap-1">
            {pendingValidation.map((execution) => (
              <Link
                key={execution.id}
                to={`/admin/checklists/${execution.id}`}
                className="text-sm text-orange-700 underline hover:text-orange-900"
              >
                {execution.template_name} — {SHIFT_LABEL[execution.shift]}
              </Link>
            ))}
          </div>
        </div>
      )}

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Checklist</th>
              <th className="px-4 py-3 font-medium">Data</th>
              <th className="px-4 py-3 font-medium">Turno</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Validação</th>
              <th className="px-4 py-3 font-medium">Executado por</th>
              <th className="px-4 py-3 font-medium">Validado por</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {executionsQuery.isLoading && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!executionsQuery.isLoading && executions.length === 0 && (
              <tr>
                <td colSpan={8} className="px-4 py-6 text-center text-gray-500">
                  Nenhum checklist neste período.
                </td>
              </tr>
            )}
            {executions.map((execution) => (
              <tr key={execution.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{execution.template_name}</td>
                <td className="px-4 py-3 text-gray-600">{formatDateBR(execution.started_at)}</td>
                <td className="px-4 py-3 text-gray-600">{SHIFT_LABEL[execution.shift]}</td>
                <td className="px-4 py-3">
                  <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${STATUS_BADGE[execution.status]}`}>
                    {STATUS_LABEL[execution.status]}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">
                  {execution.status !== 'COMPLETED' ? (
                    '—'
                  ) : execution.fully_validated ? (
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                      Validado
                    </span>
                  ) : (
                    <span className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-600">
                      Pendente
                    </span>
                  )}
                </td>
                <td className="px-4 py-3 text-gray-600">{execution.executed_by_name}</td>
                <td className="px-4 py-3 text-gray-600">
                  {execution.validated_by_names.length > 0 ? execution.validated_by_names.join(', ') : '—'}
                </td>
                <td className="px-4 py-3">
                  <Link
                    to={`/admin/checklists/${execution.id}`}
                    className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                  >
                    Abrir
                  </Link>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {isStartModalOpen && (
        <ChecklistStartFormModal templates={templates} onClose={() => setIsStartModalOpen(false)} />
      )}
    </div>
  )
}
