import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Line, LineChart, ReferenceLine, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { Modal } from '../../components/Modal'
import { getEmployeeProfile } from '../../services/dashboardService'
import { formatDateBR, formatDateTimeBR, formatDurationShort } from '../../utils/dateTime'
import { ExecutionTimelineModal } from './ExecutionTimelineModal'

interface EmployeeProfileModalProps {
  employeeId: number
  employeeName: string
  startDate?: string
  endDate?: string
  onClose: () => void
}

function StatBlock({ label, value }: { label: string; value: string | number }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-xl font-bold text-gray-900">{value}</p>
    </div>
  )
}

export function EmployeeProfileModal({ employeeId, employeeName, startDate, endDate, onClose }: EmployeeProfileModalProps) {
  const [selectedTaskTitle, setSelectedTaskTitle] = useState('')
  const [timelineHistoryId, setTimelineHistoryId] = useState<number | null>(null)

  const profileQuery = useQuery({
    queryKey: ['dashboard', 'employee-profile', employeeId, startDate, endDate],
    queryFn: () => getEmployeeProfile(employeeId, { startDate, endDate }),
  })
  const profile = profileQuery.data

  const taskTitles = useMemo(() => {
    if (!profile) return []
    return Array.from(new Set(profile.tasks.map((task) => task.task_title)))
  }, [profile])

  // Ordenado do mais antigo para o mais novo — é assim que uma "evolução ao
  // longo dos dias" faz sentido visualmente num gráfico de linha.
  const evolutionData = useMemo(() => {
    if (!profile || !selectedTaskTitle) return []
    return profile.tasks
      .filter((task) => task.task_title === selectedTaskTitle)
      .slice()
      .sort((a, b) => new Date(a.completed_at).getTime() - new Date(b.completed_at).getTime())
      .map((task) => ({
        date: formatDateBR(task.completed_at),
        minutos: Math.round((task.duration_seconds / 60) * 10) / 10,
        estimatedMinutes: task.estimated_duration_minutes,
      }))
  }, [profile, selectedTaskTitle])

  const selectedTaskSla = evolutionData.length > 0 ? evolutionData[evolutionData.length - 1].estimatedMinutes : null

  const closeButton = (
    <div className="flex justify-end">
      <button
        type="button"
        onClick={onClose}
        className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
      >
        Fechar
      </button>
    </div>
  )

  return (
    <>
    <Modal title={`Raio-X — ${employeeName}`} onClose={onClose} footer={closeButton}>
      {profileQuery.isLoading && <p className="text-sm text-gray-400">Carregando…</p>}

      {profile && (
        <div className="flex flex-col gap-4">
          <div className="grid grid-cols-3 gap-3">
            <StatBlock label="Concluídas" value={profile.completed_count} />
            <StatBlock
              label="Tempo médio"
              value={profile.avg_execution_seconds !== null ? formatDurationShort(profile.avg_execution_seconds) : '—'}
            />
            <StatBlock label="No prazo" value={profile.on_time_rate !== null ? `${profile.on_time_rate.toFixed(0)}%` : '—'} />
          </div>

          {profile.on_time_rate !== null && (
            <div className="flex items-center gap-2 text-sm">
              <span className="rounded-full bg-emerald-50 px-2.5 py-1 font-medium text-emerald-600">
                {profile.on_time_count} no prazo
              </span>
              <span className="rounded-full bg-red-50 px-2.5 py-1 font-medium text-red-600">
                {profile.late_count} com atraso
              </span>
              <span className="text-xs text-gray-400">
                (só entre as tarefas com tempo estimado configurado)
              </span>
            </div>
          )}

          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-gray-700">Tarefas concluídas no período</p>
            <div className="flex max-h-56 flex-col gap-2 overflow-y-auto">
              {profile.tasks.length === 0 ? (
                <p className="text-sm text-gray-400">Nenhuma tarefa concluída neste período.</p>
              ) : (
                profile.tasks.map((task) => (
                  <div key={task.id} className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-sm">
                    <div className="flex items-center justify-between gap-2">
                      <p className="font-medium text-gray-900">{task.task_title}</p>
                      {task.on_time !== null && (
                        <span
                          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
                            task.on_time ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
                          }`}
                        >
                          {task.on_time ? 'No prazo' : 'Com atraso'}
                        </span>
                      )}
                    </div>
                    <p className="mt-1 text-xs text-gray-500">
                      {formatDateTimeBR(task.completed_at)} — {formatDurationShort(task.duration_seconds)}
                      {task.result === 'NAO_FEITO' && ' — Não feito'}
                    </p>
                    {(task.justification || task.observation) && (
                      <p
                        className={`mt-2 rounded-lg px-2 py-1.5 text-xs ${
                          task.result === 'NAO_FEITO' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
                        }`}
                      >
                        "{task.justification ?? task.observation}"
                      </p>
                    )}
                    <button
                      type="button"
                      onClick={() => setTimelineHistoryId(task.id)}
                      className="mt-2 text-xs font-medium text-emerald-600 hover:underline"
                    >
                      Ver detalhes
                    </button>
                  </div>
                ))
              )}
            </div>
          </div>

          {taskTitles.length > 0 && (
            <div className="flex flex-col gap-2 border-t border-gray-100 pt-4">
              <label htmlFor="profile-task-select" className="text-sm font-medium text-gray-700">
                Evolução do tempo de execução por tarefa
              </label>
              <select
                id="profile-task-select"
                value={selectedTaskTitle}
                onChange={(event) => setSelectedTaskTitle(event.target.value)}
                className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
              >
                <option value="">Selecione uma tarefa…</option>
                {taskTitles.map((title) => (
                  <option key={title} value={title}>
                    {title}
                  </option>
                ))}
              </select>

              {selectedTaskTitle && (
                <div className="mt-1">
                  {evolutionData.length < 2 ? (
                    <p className="text-xs text-gray-400">
                      Só há uma conclusão dessa tarefa no período — sem histórico suficiente para um gráfico.
                    </p>
                  ) : (
                    <div className="h-48">
                      <ResponsiveContainer width="100%" height="100%">
                        <LineChart data={evolutionData} margin={{ top: 8, right: 12, left: -16, bottom: 0 }}>
                          <XAxis dataKey="date" tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                          <YAxis tick={{ fontSize: 10, fill: '#6b7280' }} axisLine={false} tickLine={false} unit="min" />
                          <Tooltip formatter={(value) => [`${value} min`, 'Tempo de execução']} />
                          <Line
                            type="monotone"
                            dataKey="minutos"
                            stroke="#10b981"
                            strokeWidth={2}
                            dot={{ r: 3 }}
                            name="Tempo de execução"
                          />
                          {selectedTaskSla !== null && (
                            <ReferenceLine
                              y={selectedTaskSla}
                              stroke="#f97316"
                              strokeDasharray="4 4"
                              label={{
                                value: `Tempo Estimado: ${selectedTaskSla}min`,
                                position: 'insideTopRight',
                                fontSize: 10,
                                fill: '#f97316',
                              }}
                            />
                          )}
                        </LineChart>
                      </ResponsiveContainer>
                    </div>
                  )}
                </div>
              )}
            </div>
          )}
        </div>
      )}
    </Modal>

    {timelineHistoryId !== null && (
      <ExecutionTimelineModal historyId={timelineHistoryId} onClose={() => setTimelineHistoryId(null)} />
    )}
    </>
  )
}
