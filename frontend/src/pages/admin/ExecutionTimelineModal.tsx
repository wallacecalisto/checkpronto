import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Lightbox } from '../../components/Lightbox'
import { Modal } from '../../components/Modal'
import { getExecutionTimeline } from '../../services/taskExecutionHistoryService'
import { formatDateTimeBR, formatDurationShort } from '../../utils/dateTime'

interface ExecutionTimelineModalProps {
  historyId: number
  onClose: () => void
}

type TimelineEvent =
  | {
      kind: 'session'
      startedAt: string
      employeeName: string
      endedAt: string | null
      leaveReason: string | null
    }
  | {
      kind: 'block'
      startedAt: string
      employeeName: string
      endedAt: string | null
      reason: string
    }
  | {
      kind: 'gap'
      startedAt: string
      endedAt: string
    }

function StatBlock({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-center">
      <p className="text-xs text-gray-500">{label}</p>
      <p className="mt-1 text-sm font-bold text-gray-900">{value}</p>
    </div>
  )
}

export function ExecutionTimelineModal({ historyId, onClose }: ExecutionTimelineModalProps) {
  const timelineQuery = useQuery({
    queryKey: ['task-execution-history', 'timeline', historyId],
    queryFn: () => getExecutionTimeline(historyId),
  })
  const timeline = timelineQuery.data
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)

  const events = useMemo<TimelineEvent[]>(() => {
    if (!timeline) return []
    const sessionEvents: TimelineEvent[] = timeline.sessions.map((session) => ({
      kind: 'session',
      startedAt: session.started_at,
      employeeName: session.employee_name,
      endedAt: session.ended_at,
      leaveReason: session.leave_reason,
    }))
    const blockEvents: TimelineEvent[] = timeline.blocks.map((block) => ({
      kind: 'block',
      startedAt: block.started_at,
      employeeName: block.blocked_by_employee_name,
      endedAt: block.ended_at,
      reason: block.reason,
    }))

    const coveredIntervals = [...timeline.sessions, ...timeline.blocks]
      .map((entry) => ({
        start: new Date(entry.started_at).getTime(),
        end: new Date(entry.ended_at ?? timeline.completed_at).getTime(),
      }))
      .sort((a, b) => a.start - b.start)

    const MIN_GAP_MS = 60 * 1000
    const gapEvents: TimelineEvent[] = []
    let cursor = new Date(timeline.started_at).getTime()
    for (const interval of coveredIntervals) {
      if (interval.start - cursor >= MIN_GAP_MS) {
        gapEvents.push({ kind: 'gap', startedAt: new Date(cursor).toISOString(), endedAt: new Date(interval.start).toISOString() })
      }
      cursor = Math.max(cursor, interval.end)
    }
    const completedAtMs = new Date(timeline.completed_at).getTime()
    if (completedAtMs - cursor >= MIN_GAP_MS) {
      gapEvents.push({ kind: 'gap', startedAt: new Date(cursor).toISOString(), endedAt: timeline.completed_at })
    }

    return [...sessionEvents, ...blockEvents, ...gapEvents].sort(
      (a, b) => new Date(a.startedAt).getTime() - new Date(b.startedAt).getTime(),
    )
  }, [timeline])

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

  const modalContent = (
    <Modal title="Detalhes da Execução" onClose={onClose} footer={closeButton}>
      {timelineQuery.isLoading && <p className="text-sm text-gray-400">Carregando…</p>}

      {timeline && (
        <div className="flex flex-col gap-4">
          <div>
            <p className="font-medium text-gray-900">{timeline.task_title}</p>
            <p className="text-xs text-gray-500">Criada por {timeline.created_by_user_name}</p>
          </div>

          <div className="grid grid-cols-3 gap-3">
            <StatBlock
              label="Tempo estimado"
              value={
                timeline.estimated_duration_minutes !== null ? `${timeline.estimated_duration_minutes}min` : '—'
              }
            />
            <StatBlock label="Tempo total" value={formatDurationShort(timeline.total_elapsed_seconds)} />
            <StatBlock label="Resultado" value={timeline.result === 'FEITO' ? 'Feito' : 'Não Feito'} />
          </div>

          {(timeline.justification || timeline.observation) && (
            <p
              className={`rounded-lg px-3 py-2 text-xs ${
                timeline.result === 'NAO_FEITO' ? 'bg-red-50 text-red-700' : 'bg-amber-50 text-amber-700'
              }`}
            >
              "{timeline.justification ?? timeline.observation}"
            </p>
          )}

          {timeline.photo_url && (
            <div className="flex flex-wrap gap-2">
              {[timeline.photo_url, ...timeline.extra_photo_urls].map((url, index) => (
                <button key={url} type="button" onClick={() => setLightboxUrl(url)} className="block">
                  <img
                    src={url}
                    alt={`Comprovação da conclusão ${index + 1}`}
                    className="h-24 w-24 cursor-zoom-in rounded-lg object-cover transition hover:opacity-90"
                  />
                </button>
              ))}
            </div>
          )}

          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-gray-700">Participantes</p>
            <div className="flex flex-col gap-1.5">
              {timeline.participants.map((participant) => (
                <div
                  key={participant.employee_id}
                  className="flex items-center justify-between rounded-lg border border-gray-100 bg-gray-50 px-3 py-2 text-sm"
                >
                  <span className="font-medium text-gray-900">{participant.employee_name}</span>
                  <span className="text-xs text-gray-500">
                    {formatDurationShort(participant.worked_duration_seconds)} trabalhados
                  </span>
                </div>
              ))}
            </div>
          </div>

          <div className="flex flex-col gap-2">
            <p className="text-sm font-medium text-gray-700">Linha do tempo</p>
            {events.length === 0 ? (
              <p className="text-xs text-gray-400">Sem sessões ou impedimentos registrados para esta execução.</p>
            ) : (
              <ol className="flex flex-col gap-2 border-l-2 border-gray-100 pl-4">
                {events.map((event, index) => (
                  <li key={index} className="relative">
                    <span
                      className={`absolute -left-[21px] top-1 h-2.5 w-2.5 rounded-full ${
                        event.kind === 'block' ? 'bg-amber-500' : event.kind === 'gap' ? 'bg-red-500' : 'bg-emerald-500'
                      }`}
                    />
                    {event.kind === 'session' && (
                      <div className="text-sm">
                        <p className="text-gray-900">
                          <span className="font-medium">{event.employeeName}</span> entrou às{' '}
                          {formatDateTimeBR(event.startedAt)}
                        </p>
                        <p className="text-xs text-gray-500">
                          {event.endedAt ? `Saiu às ${formatDateTimeBR(event.endedAt)}` : 'Ainda na tarefa'}
                          {event.leaveReason && ` — "${event.leaveReason}"`}
                        </p>
                      </div>
                    )}
                    {event.kind === 'block' && (
                      <div className="text-sm">
                        <p className="text-amber-700">
                          <span className="font-medium">{event.employeeName}</span> reportou impedimento às{' '}
                          {formatDateTimeBR(event.startedAt)}
                        </p>
                        <p className="text-xs text-amber-600">"{event.reason}"</p>
                        <p className="text-xs text-gray-500">
                          {event.endedAt ? `Retomada às ${formatDateTimeBR(event.endedAt)}` : 'Ainda impedida'}
                        </p>
                      </div>
                    )}
                    {event.kind === 'gap' && (
                      <div className="text-sm">
                        <p className="font-medium text-red-700">
                          Período Ocioso:{' '}
                          {formatDurationShort(
                            Math.round((new Date(event.endedAt).getTime() - new Date(event.startedAt).getTime()) / 1000),
                          )}
                        </p>
                        <p className="text-xs text-red-600">
                          Ninguém ativo e sem impedimento reportado entre {formatDateTimeBR(event.startedAt)} e{' '}
                          {formatDateTimeBR(event.endedAt)} — possível abandono.
                        </p>
                      </div>
                    )}
                  </li>
                ))}
              </ol>
            )}
          </div>
        </div>
      )}
    </Modal>
  )

  return (
    <>
      {modalContent}
      {lightboxUrl && (
        <Lightbox src={lightboxUrl} alt="Comprovação da conclusão" onClose={() => setLightboxUrl(null)} />
      )}
    </>
  )
}
