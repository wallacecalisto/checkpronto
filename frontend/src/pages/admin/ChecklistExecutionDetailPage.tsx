import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { Link, useParams } from 'react-router-dom'
import { useAuth } from '../../auth/useAuth'
import { Lightbox } from '../../components/Lightbox'
import { getApiErrorCode, getApiErrorMessage } from '../../services/apiClient'
import {
  answerChecklistItem,
  completeChecklistExecution,
  getChecklistExecution,
  validateChecklistItem,
} from '../../services/checklistService'
import { SHIFT_LABEL, type ChecklistExecutionItem, type ChecklistItemResponse } from '../../types/checklistExecution'
import { formatDateTimeBR } from '../../utils/dateTime'

const RESULT_TAG_CLASS: Record<string, string> = {
  APROVADO: 'bg-emerald-50 text-emerald-600',
  DIVERGENTE: 'bg-red-50 text-red-600',
}

export function ChecklistExecutionDetailPage() {
  const params = useParams<{ id: string }>()
  const executionId = Number(params.id)
  const queryClient = useQueryClient()
  const { user } = useAuth()

  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [validatingItemId, setValidatingItemId] = useState<number | null>(null)
  const [validationResult, setValidationResult] = useState<'APROVADO' | 'DIVERGENTE'>('APROVADO')
  const [validationJustification, setValidationJustification] = useState('')
  const [lightboxUrl, setLightboxUrl] = useState<string | null>(null)

  const executionQuery = useQuery({
    queryKey: ['checklists', 'admin', executionId],
    queryFn: () => getChecklistExecution(executionId),
  })

  const invalidate = () => {
    queryClient.invalidateQueries({ queryKey: ['checklists', 'admin', executionId] })
    queryClient.invalidateQueries({ queryKey: ['checklists', 'admin'] })
  }

  const answerMutation = useMutation({
    mutationFn: ({ itemId, response, observation }: { itemId: number; response: ChecklistItemResponse; observation?: string }) =>
      answerChecklistItem(executionId, itemId, { response, observation }),
    onSuccess: invalidate,
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  const completeMutation = useMutation({
    mutationFn: () => completeChecklistExecution(executionId),
    onSuccess: invalidate,
    onError: (error: unknown) => {
      if (getApiErrorCode(error) === 'CHECKLIST_INCOMPLETE') {
        setErrorMessage('Existem itens obrigatórios sem resposta — responda todos antes de concluir.')
      } else {
        setErrorMessage(getApiErrorMessage(error))
      }
    },
  })

  const validateMutation = useMutation({
    mutationFn: ({ itemId, result, justification }: { itemId: number; result: 'APROVADO' | 'DIVERGENTE'; justification?: string }) =>
      validateChecklistItem(executionId, itemId, { result, justification }),
    onSuccess: () => {
      setValidatingItemId(null)
      setValidationJustification('')
      invalidate()
    },
    onError: (error: unknown) => {
      if (getApiErrorCode(error) === 'SAME_USER_VALIDATION_FORBIDDEN') {
        setErrorMessage('Quem executou o checklist não pode validar seus próprios itens.')
      } else {
        setErrorMessage(getApiErrorMessage(error))
      }
    },
  })

  function beginValidating(item: ChecklistExecutionItem): void {
    setValidatingItemId(item.id)
    setValidationResult('APROVADO')
    setValidationJustification('')
    setErrorMessage(null)
  }

  function confirmValidation(itemId: number): void {
    setErrorMessage(null)
    validateMutation.mutate({
      itemId,
      result: validationResult,
      justification: validationResult === 'DIVERGENTE' ? validationJustification.trim() : undefined,
    })
  }

  const execution = executionQuery.data
  const isInProgress = execution?.status === 'IN_PROGRESS'
  const isCompleted = execution?.status === 'COMPLETED'
  const isOwnExecution = execution !== undefined && execution.executed_by_user_id === user?.id

  return (
    <div className="flex flex-col gap-6">
      <div>
        <Link to="/admin/checklists" className="text-sm text-emerald-600 hover:underline">
          ← Voltar para Checklists
        </Link>
        {execution && (
          <div className="mt-1 flex flex-wrap items-center gap-3">
            <h1 className="text-xl font-semibold text-gray-900">{execution.template_name}</h1>
            <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-600">
              {SHIFT_LABEL[execution.shift]}
            </span>
            <span className="text-xs text-gray-400">Iniciado em {formatDateTimeBR(execution.started_at)}</span>
          </div>
        )}
      </div>

      {errorMessage && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {errorMessage}
        </p>
      )}

      {executionQuery.isLoading && <p className="text-gray-500">Carregando…</p>}

      {execution && (
        <div className="flex flex-col gap-3">
          {execution.items.map((item) => (
            <div key={item.id} className="rounded-xl border border-gray-200 bg-white p-4 shadow-sm">
              <p className="font-medium text-gray-900">{item.item_description_snapshot}</p>

              {isInProgress && (
                <div className="mt-3 flex flex-col gap-2">
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => answerMutation.mutate({ itemId: item.id, response: 'OK', observation: item.observation ?? undefined })}
                      disabled={answerMutation.isPending}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                        item.response === 'OK'
                          ? 'bg-emerald-500 text-white'
                          : 'border border-gray-200 text-gray-600 hover:bg-gray-100'
                      }`}
                    >
                      OK
                    </button>
                    <button
                      type="button"
                      onClick={() => answerMutation.mutate({ itemId: item.id, response: 'DIVERGENTE', observation: item.observation ?? undefined })}
                      disabled={answerMutation.isPending}
                      className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition disabled:cursor-not-allowed disabled:opacity-50 ${
                        item.response === 'DIVERGENTE'
                          ? 'bg-red-500 text-white'
                          : 'border border-red-200 text-red-600 hover:bg-red-50'
                      }`}
                    >
                      Divergente
                    </button>
                  </div>
                  <textarea
                    defaultValue={item.observation ?? ''}
                    onBlur={(event) => {
                      if (item.response === null) return
                      answerMutation.mutate({ itemId: item.id, response: item.response, observation: event.target.value || undefined })
                    }}
                    placeholder="Observação (opcional)"
                    rows={2}
                    className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                  />
                </div>
              )}

              {isCompleted && (
                <div className="mt-3 flex flex-col gap-2">
                  <div className="flex flex-wrap items-center gap-2 text-sm text-gray-600">
                    <span
                      className={`rounded-full px-2.5 py-1 text-xs font-medium ${
                        item.response === 'OK' ? 'bg-emerald-50 text-emerald-600' : 'bg-red-50 text-red-600'
                      }`}
                    >
                      {item.response ?? 'Sem resposta'}
                    </span>
                    {item.observation && <span className="text-xs text-gray-500">{item.observation}</span>}
                  </div>

                  {item.photo_url && (
                    <div className="flex flex-wrap gap-2">
                      {[item.photo_url, ...item.extra_photo_urls].map((url, index) => (
                        <button key={url} type="button" onClick={() => setLightboxUrl(url)} className="block w-fit">
                          <img
                            src={url}
                            alt={`Foto enviada pelo operador ${index + 1}`}
                            className="h-24 w-24 cursor-zoom-in rounded-lg border border-gray-200 object-cover transition hover:opacity-90"
                          />
                        </button>
                      ))}
                    </div>
                  )}

                  {item.validation ? (
                    <div className="rounded-lg border border-gray-100 bg-gray-50 p-3 text-sm">
                      <span
                        className={`rounded-full px-2.5 py-1 text-xs font-medium ${RESULT_TAG_CLASS[item.validation.result]}`}
                      >
                        {item.validation.result === 'APROVADO' ? 'Aprovado' : 'Divergente'}
                      </span>
                      {item.validation.justification && (
                        <p className="mt-1 text-xs text-gray-600">Justificativa: {item.validation.justification}</p>
                      )}
                      <p className="mt-1 text-xs text-gray-400">
                        Validado em {formatDateTimeBR(item.validation.validated_at)}
                      </p>
                    </div>
                  ) : item.response === null ? (
                    <p className="text-xs text-gray-400">Item não respondido — nada para validar.</p>
                  ) : isOwnExecution ? (
                    <p className="text-xs text-gray-400">
                      Aguardando validação de outro gestor ou líder — quem executou o checklist não pode validar seus
                      próprios itens.
                    </p>
                  ) : validatingItemId === item.id ? (
                    <div className="flex flex-col gap-2 rounded-lg border border-gray-200 p-3">
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setValidationResult('APROVADO')}
                          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                            validationResult === 'APROVADO'
                              ? 'bg-emerald-500 text-white'
                              : 'border border-gray-200 text-gray-600 hover:bg-gray-100'
                          }`}
                        >
                          Aprovar
                        </button>
                        <button
                          type="button"
                          onClick={() => setValidationResult('DIVERGENTE')}
                          className={`rounded-lg px-3 py-1.5 text-xs font-semibold transition ${
                            validationResult === 'DIVERGENTE'
                              ? 'bg-red-500 text-white'
                              : 'border border-red-200 text-red-600 hover:bg-red-50'
                          }`}
                        >
                          Divergente
                        </button>
                      </div>
                      {validationResult === 'DIVERGENTE' && (
                        <textarea
                          value={validationJustification}
                          onChange={(event) => setValidationJustification(event.target.value)}
                          placeholder="Justificativa (obrigatória)"
                          rows={2}
                          className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
                        />
                      )}
                      <div className="flex gap-2">
                        <button
                          type="button"
                          onClick={() => setValidatingItemId(null)}
                          className="flex-1 rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                        >
                          Cancelar
                        </button>
                        <button
                          type="button"
                          disabled={
                            validateMutation.isPending ||
                            (validationResult === 'DIVERGENTE' && validationJustification.trim().length === 0)
                          }
                          onClick={() => confirmValidation(item.id)}
                          className="flex-1 rounded-lg bg-emerald-500 px-3 py-1.5 text-xs font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
                        >
                          Confirmar
                        </button>
                      </div>
                    </div>
                  ) : (
                    <button
                      type="button"
                      onClick={() => beginValidating(item)}
                      className="self-start rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Validar
                    </button>
                  )}
                </div>
              )}
            </div>
          ))}

          {isInProgress && (
            <button
              type="button"
              onClick={() => {
                setErrorMessage(null)
                completeMutation.mutate()
              }}
              disabled={completeMutation.isPending}
              className="self-start rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
            >
              {completeMutation.isPending ? 'Concluindo…' : 'Concluir Checklist'}
            </button>
          )}
        </div>
      )}

      {lightboxUrl && (
        <Lightbox src={lightboxUrl} alt="Foto enviada pelo operador" onClose={() => setLightboxUrl(null)} />
      )}
    </div>
  )
}
