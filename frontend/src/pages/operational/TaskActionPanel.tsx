import { useEffect, useState } from 'react'
import { MultiPhotoPicker } from '../../components/MultiPhotoPicker'
import { getApiErrorMessage } from '../../services/apiClient'
import type { TaskAssignment } from '../../types/taskAssignment'
import type { InlinePinAuthPerson } from './InlinePinAuth'

interface TaskActionPanelProps {
  assignment: TaskAssignment
  person: InlinePinAuthPerson
  requireLivePhotoOnly: boolean
  onComplete: (photoFiles: File[]) => Promise<void>
  onLeave: () => Promise<void>
  onBlock: (reason: string) => Promise<void>
  onClose: () => void
}

type PanelMode = 'actions' | 'completing' | 'blocking'

export function TaskActionPanel({
  assignment,
  person,
  requireLivePhotoOnly,
  onComplete,
  onLeave,
  onBlock,
  onClose,
}: TaskActionPanelProps) {
  const [mode, setMode] = useState<PanelMode>('actions')
  const [photoFiles, setPhotoFiles] = useState<File[]>([])
  const [blockReasonText, setBlockReasonText] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  function handleConcluirClick(): void {
    if (assignment.requires_photo_proof) {
      setErrorMessage(null)
      setMode('completing')
      return
    }
    void runComplete([])
  }

  async function runComplete(photos: File[]): Promise<void> {
    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      await onComplete(photos)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function runLeave(): Promise<void> {
    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      await onLeave()
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  async function runBlock(): Promise<void> {
    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      await onBlock(blockReasonText.trim())
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setIsSubmitting(false)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-sm flex-col rounded-3xl border border-slate-200 bg-white shadow-2xl">
        <div className="shrink-0 px-6 pt-6 sm:px-8 sm:pt-8">
          <div className="mb-4 flex items-start justify-between gap-3">
            <div>
              <h2 className="text-lg font-semibold text-slate-800">{assignment.task_title}</h2>
              <p className="text-sm text-slate-500">
                Com: <span className="font-medium text-slate-700">{person.name}</span>
              </p>
            </div>
            <button
              type="button"
              onClick={onClose}
              disabled={isSubmitting}
              aria-label="Fechar"
              className="shrink-0 rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              ✕
            </button>
          </div>

          {errorMessage && (
            <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-600">
              {errorMessage}
            </p>
          )}
        </div>

        <div className="overflow-y-auto px-6 pb-6 sm:px-8 sm:pb-8">
          {mode === 'actions' && (
            <div className="flex flex-col gap-3">
              <button
                type="button"
                onClick={handleConcluirClick}
                disabled={isSubmitting}
                className="w-full rounded-2xl bg-emerald-500 px-8 py-6 text-xl font-bold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
              >
                {isSubmitting ? 'Concluindo…' : 'Concluir'}
              </button>
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => void runLeave()}
                  disabled={isSubmitting}
                  className="flex-1 rounded-xl border-2 border-slate-200 px-4 py-3 text-sm font-semibold text-slate-600 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Sair da Tarefa
                </button>
                <button
                  type="button"
                  onClick={() => setMode('blocking')}
                  disabled={isSubmitting}
                  className="flex-1 rounded-xl border-2 border-amber-300 px-4 py-3 text-sm font-semibold text-amber-700 transition hover:bg-amber-50 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Reportar Impedimento
                </button>
              </div>
            </div>
          )}

          {mode === 'completing' && (
            <div className="flex flex-col gap-3">
              <MultiPhotoPicker
                id="task-action-photo"
                files={photoFiles}
                onChange={setPhotoFiles}
                requireLiveCapture={requireLivePhotoOnly}
                disabled={isSubmitting}
                requiredLabel="Foto de comprovação (obrigatória)"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setMode('actions')
                    setPhotoFiles([])
                    setErrorMessage(null)
                  }}
                  disabled={isSubmitting}
                  className="flex-1 rounded-xl border-2 border-slate-200 px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={isSubmitting || photoFiles.length === 0}
                  onClick={() => void runComplete(photoFiles)}
                  className="flex-1 rounded-xl bg-emerald-500 px-6 py-3 text-sm font-bold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
                >
                  {isSubmitting ? 'Concluindo…' : 'Confirmar'}
                </button>
              </div>
            </div>
          )}

          {mode === 'blocking' && (
            <div className="flex flex-col gap-3">
              <label htmlFor="task-action-block-reason" className="text-sm font-medium text-slate-700">
                Motivo do impedimento (obrigatório)
              </label>
              <textarea
                id="task-action-block-reason"
                value={blockReasonText}
                onChange={(event) => setBlockReasonText(event.target.value)}
                rows={2}
                className="rounded-xl border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 outline-none placeholder:text-slate-400 focus:border-amber-500 focus:ring-2 focus:ring-amber-500/20"
                placeholder="Ex.: faltou insumo, equipamento quebrou…"
              />
              <div className="flex gap-2">
                <button
                  type="button"
                  onClick={() => {
                    setMode('actions')
                    setBlockReasonText('')
                    setErrorMessage(null)
                  }}
                  disabled={isSubmitting}
                  className="flex-1 rounded-xl border-2 border-slate-200 px-6 py-3 text-sm font-semibold text-slate-700 transition hover:bg-slate-100 disabled:cursor-not-allowed disabled:opacity-50"
                >
                  Cancelar
                </button>
                <button
                  type="button"
                  disabled={isSubmitting || blockReasonText.trim().length === 0}
                  onClick={() => void runBlock()}
                  className="flex-1 rounded-xl bg-amber-500 px-6 py-3 text-sm font-bold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-amber-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
                >
                  {isSubmitting ? 'Enviando…' : 'Confirmar'}
                </button>
              </div>
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
