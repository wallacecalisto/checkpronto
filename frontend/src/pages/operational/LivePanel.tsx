import { formatMMSS, isTaskOverdue, slaProgressPercent, useTaskTimer } from '../../hooks/useTaskTimer'
import type { TaskAssignment } from '../../types/taskAssignment'

interface LivePanelProps {
  assignments: TaskAssignment[]
  hideTimer?: boolean
}

export function LivePanel({ assignments, hideTimer = false }: LivePanelProps) {
  if (assignments.length === 0) {
    return (
      <div className="rounded-2xl border border-gray-200 bg-white p-6 text-center text-gray-500 shadow-sm">
        Nenhuma tarefa em andamento agora.
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3">
      {assignments.map((assignment) => (
        <LiveTaskRow key={assignment.id} assignment={assignment} hideTimer={hideTimer} />
      ))}
    </div>
  )
}

function LiveTaskRow({ assignment, hideTimer }: { assignment: TaskAssignment; hideTimer: boolean }) {
  const elapsed = useTaskTimer(assignment.elapsed_seconds)
  const overdue = isTaskOverdue(assignment.elapsed_seconds ?? 0, assignment.estimated_duration_minutes)
  const percent = slaProgressPercent(assignment.elapsed_seconds ?? 0, assignment.estimated_duration_minutes)
  const slaLabel =
    assignment.estimated_duration_minutes !== null ? formatMMSS(assignment.estimated_duration_minutes * 60) : null

  const participantNames = assignment.active_participants.map((participant) => participant.employee_name)
  const employeeLabel = participantNames.length > 0 ? participantNames.join(', ') : 'Ninguém no momento'

  return (
    <div className="flex flex-col gap-2.5 rounded-2xl border border-gray-200 bg-white px-5 py-4 shadow-sm">
      <div className="flex items-center justify-between gap-4">
        <p className="min-w-0 truncate text-gray-900">
          <span className="font-medium">{employeeLabel}</span>{' '}
          <span className="text-gray-500">fazendo</span> <span className="font-medium">{assignment.task_title}</span>
        </p>
        {!hideTimer && (
          <span
            className={`shrink-0 rounded-full px-3 py-1 font-mono text-sm font-semibold ${
              overdue ? 'bg-orange-50 text-orange-600' : 'bg-indigo-50 text-indigo-600'
            }`}
          >
            {slaLabel ? `${elapsed} / ${slaLabel}` : elapsed}
          </span>
        )}
      </div>

      {!hideTimer && percent !== null && (
        <div className="h-1.5 w-full overflow-hidden rounded-full bg-gray-100">
          <div
            className={`h-full rounded-full transition-all duration-500 ${overdue ? 'bg-orange-500' : 'bg-indigo-500'}`}
            style={{ width: `${Math.min(100, Math.max(0, percent))}%` }}
          />
        </div>
      )}
    </div>
  )
}
