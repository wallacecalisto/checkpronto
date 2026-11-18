import { useEffect, useRef, useState } from 'react'
import { Lightbox } from '../../components/Lightbox'
import { isTaskOverdue, useTaskTimer } from '../../hooks/useTaskTimer'
import type { TaskAssignment } from '../../types/taskAssignment'
import { KanbanColumn } from './KanbanColumn'

interface SectorTaskListProps {
  assignments: TaskAssignment[]
  isBusy: boolean
  hideTaskTimer: boolean
  onStartOrJoin: (assignment: TaskAssignment) => void
  onResume: (assignment: TaskAssignment) => void
  onOverdue: () => void
}

const RESULT_TAG: Record<string, string> = { FEITO: 'Feito', NAO_FEITO: 'Não Feito' }
const RESULT_TAG_CLASS: Record<string, string> = {
  FEITO: 'bg-emerald-50 text-emerald-600',
  NAO_FEITO: 'bg-red-50 text-red-600',
}

function ElapsedBadge({ assignment, onOverdue }: { assignment: TaskAssignment; onOverdue: () => void }) {
  const elapsed = useTaskTimer(assignment.elapsed_seconds)
  const overdue = isTaskOverdue(assignment.elapsed_seconds ?? 0, assignment.estimated_duration_minutes)

  const onOverdueRef = useRef(onOverdue)
  onOverdueRef.current = onOverdue

  useEffect(() => {
    if (overdue) onOverdueRef.current()
  }, [overdue])

  return (
    <span
      className={`shrink-0 rounded-full px-2.5 py-1 font-mono text-xs font-semibold ${
        overdue ? 'bg-orange-50 text-orange-600' : 'bg-indigo-50 text-indigo-600'
      }`}
    >
      {elapsed}
    </span>
  )
}

interface TaskCardProps {
  assignment: TaskAssignment
  isBusy: boolean
  hideTaskTimer: boolean
  onStartOrJoin: (assignment: TaskAssignment) => void
  onResume: (assignment: TaskAssignment) => void
  onOpenPhoto: (url: string) => void
  onOverdue: () => void
}

function TaskCard({ assignment, isBusy, hideTaskTimer, onStartOrJoin, onResume, onOpenPhoto, onOverdue }: TaskCardProps) {
  const isPending = assignment.status === 'PENDING'
  const isInProgress = assignment.status === 'IN_PROGRESS'
  const isBlocked = assignment.status === 'BLOCKED'
  const isCompleted = assignment.status === 'COMPLETED'
  const isAbandoned = isInProgress && assignment.active_participants.length === 0

  return (
    <div
      className={`rounded-2xl border p-4 shadow-sm ${
        isCompleted
          ? 'border-slate-200 bg-slate-50 opacity-60'
          : isBlocked || isAbandoned
            ? 'border-orange-300 bg-orange-50'
            : 'border-slate-200 bg-white'
      }`}
    >
      <div className="flex items-start justify-between gap-3">
        <div>
          <p className="font-medium text-slate-800">{assignment.task_title}</p>
          {assignment.task_description && <p className="mt-1 text-sm text-slate-500">{assignment.task_description}</p>}
        </div>
        <div className="flex shrink-0 items-center gap-2">
          {isInProgress && !hideTaskTimer && <ElapsedBadge assignment={assignment} onOverdue={onOverdue} />}
          {isAbandoned && (
            <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-medium text-orange-700">
              Parada / Sem responsável
            </span>
          )}
          {isBlocked && (
            <span className="rounded-full bg-orange-100 px-2.5 py-1 text-xs font-medium text-orange-700">Impedida</span>
          )}
          {isCompleted && assignment.result && (
            <span className={`rounded-full px-2.5 py-1 text-xs font-medium ${RESULT_TAG_CLASS[assignment.result]}`}>
              {RESULT_TAG[assignment.result]}
            </span>
          )}
        </div>
      </div>

      {isInProgress && assignment.active_participants.length > 0 && (
        <p className="mt-2 text-xs text-slate-500">
          Com:{' '}
          <span className="font-medium text-slate-700">
            {assignment.active_participants.map((participant) => participant.employee_name).join(', ')}
          </span>
        </p>
      )}

      {isCompleted && (assignment.justification || assignment.observation) && (
        <div className="mt-2 flex flex-col gap-1 text-xs text-slate-500">
          {assignment.justification && <p>Justificativa: {assignment.justification}</p>}
          {assignment.observation && <p>Observação: {assignment.observation}</p>}
        </div>
      )}

      {isCompleted && assignment.photo_url && (
        <div className="mt-2 flex flex-wrap gap-2">
          {[assignment.photo_url, ...assignment.extra_photo_urls].map((url, index) => (
            <button key={url} type="button" onClick={() => onOpenPhoto(url)} className="block">
              <img
                src={url}
                alt={`Foto enviada ${index + 1}`}
                className="h-12 w-12 cursor-zoom-in rounded-lg border border-slate-200 object-cover"
              />
            </button>
          ))}
        </div>
      )}

      {isBlocked && assignment.block_reason && (
        <p className="mt-2 text-xs text-orange-700">Motivo do impedimento: {assignment.block_reason}</p>
      )}

      {(isPending || isInProgress) && (
        <button
          type="button"
          onClick={() => onStartOrJoin(assignment)}
          disabled={isBusy}
          className="mt-3 w-full rounded-xl bg-indigo-500 px-8 py-4 text-lg font-bold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-indigo-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        >
          {assignment.active_participants.length === 0 ? 'Iniciar Tarefa' : 'Entrar na Tarefa / Encerrar Tarefa'}
        </button>
      )}

      {isBlocked && (
        <button
          type="button"
          onClick={() => onResume(assignment)}
          disabled={isBusy}
          className="mt-3 w-full rounded-xl bg-amber-500 px-8 py-4 text-lg font-bold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-amber-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        >
          Retomar
        </button>
      )}
    </div>
  )
}

export function SectorTaskList({
  assignments,
  isBusy,
  hideTaskTimer,
  onStartOrJoin,
  onResume,
  onOverdue,
}: SectorTaskListProps) {
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)

  if (assignments.length === 0) {
    return <p className="text-center text-slate-500">Nenhuma tarefa para hoje neste setor.</p>
  }

  const pendingColumn = assignments.filter((a) => a.status === 'PENDING' || a.status === 'BLOCKED')
  const inProgressColumn = assignments.filter((a) => a.status === 'IN_PROGRESS')
  const completedColumn = assignments.filter((a) => a.status === 'COMPLETED')

  function renderCard(assignment: TaskAssignment) {
    return (
      <TaskCard
        key={assignment.id}
        assignment={assignment}
        isBusy={isBusy}
        hideTaskTimer={hideTaskTimer}
        onStartOrJoin={onStartOrJoin}
        onResume={onResume}
        onOpenPhoto={setLightboxUrl}
        onOverdue={onOverdue}
      />
    )
  }

  return (
    <div>
      <div className="grid grid-cols-1 gap-4 md:grid-cols-3">
        <KanbanColumn title="Pendentes" count={pendingColumn.length} emptyLabel="Nenhuma tarefa pendente.">
          {pendingColumn.map(renderCard)}
        </KanbanColumn>
        <KanbanColumn title="Em Andamento" count={inProgressColumn.length} emptyLabel="Nenhuma tarefa em andamento.">
          {inProgressColumn.map(renderCard)}
        </KanbanColumn>
        <KanbanColumn title="Concluídas" count={completedColumn.length} emptyLabel="Nenhuma tarefa concluída hoje ainda.">
          {completedColumn.map(renderCard)}
        </KanbanColumn>
      </div>

      {lightboxUrl && <Lightbox src={lightboxUrl} alt="Foto enviada" onClose={() => setLightboxUrl(null)} />}
    </div>
  )
}
