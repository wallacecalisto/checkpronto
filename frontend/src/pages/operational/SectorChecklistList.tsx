import { useState } from 'react'
import { useQuery, useQueryClient } from '@tanstack/react-query'
import { MultiPhotoPicker } from '../../components/MultiPhotoPicker'
import { getApiErrorField, getApiErrorMessage } from '../../services/apiClient'
import {
  answerChecklistItem,
  completeChecklistExecution,
  listChecklistExecutions,
  uploadChecklistItemPhoto,
} from '../../services/checklistService'
import { listChecklistTemplates } from '../../services/checklistTemplateService'
import type {
  ChecklistExecution,
  ChecklistExecutionItem,
  ChecklistItemResponse,
  Shift,
} from '../../types/checklistExecution'
import { suggestedShift } from '../../types/checklistExecution'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import { toISODateString } from '../../utils/dateTime'
import { KanbanColumn } from './KanbanColumn'

interface SectorChecklistListProps {
  sectorId: number
  sectorShift: string
  isBusy: boolean
  requireLivePhotoOnly: boolean
  onRequestStart: (template: ChecklistTemplate, shift: Shift, onStarted: (execution: ChecklistExecution) => void) => void
}

interface ChecklistItemRowProps {
  item: ChecklistExecutionItem
  disabled: boolean
  requireLiveCapture: boolean
  onAnswer: (itemId: number, response: ChecklistItemResponse, observation: string, photoFiles: File[]) => void
}

const RESPONSE_LABEL: Record<ChecklistItemResponse, string> = { OK: 'OK', DIVERGENTE: 'Divergente' }
const RESPONSE_CLASS: Record<ChecklistItemResponse, string> = {
  OK: 'bg-emerald-50 text-emerald-600',
  DIVERGENTE: 'bg-red-50 text-red-600',
}

function ChecklistItemRow({ item, disabled, requireLiveCapture, onAnswer }: ChecklistItemRowProps) {
  const [observation, setObservation] = useState(item.observation ?? '')
  const [photoFiles, setPhotoFiles] = useState<File[]>([])

  const hasPhoto = Boolean(item.photo_url) || photoFiles.length > 0
  const photoMissing = item.requires_photo && !hasPhoto
  const answerDisabled = disabled || photoMissing

  return (
    <div className="rounded-xl border border-slate-100 bg-white p-3 text-sm shadow-sm">
      <div className="flex items-start justify-between gap-2">
        <p className="font-medium text-slate-800">{item.item_description_snapshot}</p>
        {item.response && (
          <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${RESPONSE_CLASS[item.response]}`}>
            {RESPONSE_LABEL[item.response]}
          </span>
        )}
      </div>

      {item.requires_photo && (
        <div className="mt-2">
          <MultiPhotoPicker
            id={`checklist-item-photo-${item.id}`}
            files={photoFiles}
            onChange={setPhotoFiles}
            requireLiveCapture={requireLiveCapture}
            disabled={disabled}
            requiredLabel="Foto de comprovação (obrigatória)"
          />
          {item.photo_url && photoFiles.length === 0 && (
            <p className="mt-1.5 text-xs text-slate-500">Já tem uma foto enviada — anexar novas substitui.</p>
          )}
          {photoMissing && <p className="mt-1.5 text-xs text-amber-600">Este item exige uma foto para ser respondido.</p>}
        </div>
      )}

      <textarea
        value={observation}
        onChange={(event) => setObservation(event.target.value)}
        rows={1}
        placeholder="Observação (opcional)"
        disabled={disabled}
        className="mt-2 w-full rounded-lg border border-slate-200 bg-slate-50 px-3 py-2 text-slate-800 outline-none placeholder:text-slate-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
      />
      <div className="mt-2 flex gap-2">
        <button
          type="button"
          onClick={() => onAnswer(item.id, 'OK', observation.trim(), photoFiles)}
          disabled={answerDisabled}
          className="flex-1 rounded-lg bg-emerald-500 px-3 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        >
          OK
        </button>
        <button
          type="button"
          onClick={() => onAnswer(item.id, 'DIVERGENTE', observation.trim(), photoFiles)}
          disabled={answerDisabled}
          className="flex-1 rounded-lg border-2 border-red-200 px-3 py-3 text-sm font-semibold text-red-600 transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-red-50 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-none"
        >
          Divergente
        </button>
      </div>
    </div>
  )
}

interface TemplateCardProps {
  template: ChecklistTemplate
  inProgress: ChecklistExecution | undefined
  completedToday: boolean
  isBusy: boolean
  onContinue: (execution: ChecklistExecution) => void
  onRequestStart: (template: ChecklistTemplate) => void
}

function TemplateCard({ template, inProgress, completedToday, isBusy, onContinue, onRequestStart }: TemplateCardProps) {
  return (
    <div
      className={`flex items-center justify-between gap-2 rounded-xl border border-slate-100 bg-white p-3 shadow-sm ${
        completedToday && !inProgress ? 'opacity-60' : ''
      }`}
    >
      <div>
        <div className="flex items-center gap-2">
          <p className="font-medium text-slate-800">{template.name}</p>
          {completedToday && (
            <span className="shrink-0 rounded-full bg-emerald-50 px-2 py-0.5 text-xs font-medium text-emerald-600">
              Concluído hoje
            </span>
          )}
        </div>
        {inProgress && <p className="text-xs text-indigo-600">Em andamento, iniciado por {inProgress.executed_by_name}</p>}
      </div>
      {inProgress ? (
        <button
          type="button"
          onClick={() => onContinue(inProgress)}
          className="shrink-0 rounded-lg bg-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-indigo-600 hover:shadow-md"
        >
          Continuar
        </button>
      ) : (
        <button
          type="button"
          onClick={() => onRequestStart(template)}
          disabled={isBusy}
          className="shrink-0 rounded-lg bg-indigo-500 px-4 py-3 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-indigo-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0 disabled:hover:shadow-sm"
        >
          Iniciar
        </button>
      )}
    </div>
  )
}

export function SectorChecklistList({
  sectorId,
  sectorShift,
  isBusy,
  requireLivePhotoOnly,
  onRequestStart,
}: SectorChecklistListProps) {
  const queryClient = useQueryClient()
  const [activeExecution, setActiveExecution] = useState<ChecklistExecution | null>(null)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isAnswering, setIsAnswering] = useState(false)

  const templatesQuery = useQuery({
    queryKey: ['checklist-templates', 'operational', sectorId],
    queryFn: () => listChecklistTemplates({ activeOnly: true, sectorId }),
  })
  const templates = (templatesQuery.data ?? []).filter((template) => template.shift === sectorShift)

  const now = new Date()
  const paddedFrom = toISODateString(new Date(now.getFullYear(), now.getMonth(), now.getDate() - 1))
  const paddedTo = toISODateString(new Date(now.getFullYear(), now.getMonth(), now.getDate() + 1))
  const todayLocalStr = toISODateString(now)

  const inProgressQuery = useQuery({
    queryKey: ['checklist-executions', 'in-progress'],
    queryFn: () => listChecklistExecutions({ status: 'IN_PROGRESS' }),
    refetchInterval: 5000,
  })
  const inProgressExecutions = inProgressQuery.data ?? []

  const completedRecentlyQuery = useQuery({
    queryKey: ['checklist-executions', 'completed', 'recent', paddedFrom, paddedTo],
    queryFn: () => listChecklistExecutions({ status: 'COMPLETED', startedFrom: paddedFrom, startedTo: paddedTo }),
    refetchInterval: 5000,
  })
  const completedTodayExecutions = (completedRecentlyQuery.data ?? []).filter(
    (execution) => execution.finished_at !== null && toISODateString(new Date(execution.finished_at)) === todayLocalStr,
  )
  const completedTodayTemplateIds = new Set(completedTodayExecutions.map((execution) => execution.template_id))

  const pendingTemplates = templates.filter(
    (template) => !completedTodayTemplateIds.has(template.id) || inProgressExecutions.some((e) => e.template_id === template.id),
  )
  const completedTemplates = templates.filter(
    (template) => completedTodayTemplateIds.has(template.id) && !inProgressExecutions.some((e) => e.template_id === template.id),
  )

  function findInProgressExecution(templateId: number): ChecklistExecution | undefined {
    return inProgressExecutions.find((execution) => execution.template_id === templateId)
  }

  function wasCompletedToday(templateId: number): boolean {
    return completedTodayTemplateIds.has(templateId)
  }

  async function refreshInProgressList(): Promise<void> {
    await queryClient.invalidateQueries({ queryKey: ['checklist-executions', 'in-progress'] })
    // Prefixo só (sem paddedFrom/paddedTo) — invalida a query independente
    // da janela de datas calculada nesta renderização.
    await queryClient.invalidateQueries({ queryKey: ['checklist-executions', 'completed', 'recent'] })
  }

  async function handleAnswer(
    itemId: number,
    response: ChecklistItemResponse,
    observation: string,
    photoFiles: File[],
  ): Promise<void> {
    if (!activeExecution) return
    setErrorMessage(null)
    setIsAnswering(true)
    try {
      const photoUrls: string[] = []
      for (const photoFile of photoFiles) {
        const uploadResult = await uploadChecklistItemPhoto(activeExecution.id, itemId, { photo: photoFile })
        photoUrls.push(uploadResult.photo_url)
      }
      const updatedItem = await answerChecklistItem(activeExecution.id, itemId, {
        response,
        observation: observation || undefined,
        photo_url: photoUrls[0],
        extra_photo_urls: photoUrls.slice(1),
      })
      setActiveExecution({
        ...activeExecution,
        items: activeExecution.items.map((item) => (item.id === updatedItem.id ? updatedItem : item)),
      })
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
    } finally {
      setIsAnswering(false)
    }
  }

  async function handleComplete(): Promise<void> {
    if (!activeExecution) return
    setErrorMessage(null)
    setIsAnswering(true)
    try {
      const completed = await completeChecklistExecution(activeExecution.id)
      setActiveExecution(completed)
      await refreshInProgressList()
    } catch (error) {
      const missingItemIds = getApiErrorField(error, 'missing_item_ids')
      setErrorMessage(
        Array.isArray(missingItemIds) && missingItemIds.length > 0
          ? 'Ainda há itens obrigatórios sem resposta.'
          : getApiErrorMessage(error),
      )
    } finally {
      setIsAnswering(false)
    }
  }

  if (activeExecution) {
    const isCompleted = activeExecution.status === 'COMPLETED'
    return (
      <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
        <div className="flex items-center justify-between gap-2">
          <p className="font-medium text-slate-800">{activeExecution.template_name}</p>
          <span
            className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-medium ${
              isCompleted ? 'bg-emerald-50 text-emerald-600' : 'bg-indigo-50 text-indigo-600'
            }`}
          >
            {isCompleted ? 'Concluído' : 'Em andamento'}
          </span>
        </div>
        <p className="text-xs text-slate-500">Iniciado por {activeExecution.executed_by_name}</p>

        {errorMessage && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {errorMessage}
          </p>
        )}

        <div className="flex flex-col gap-2">
          {activeExecution.items.map((item) => (
            <ChecklistItemRow
              key={item.id}
              item={item}
              disabled={isAnswering || isCompleted}
              requireLiveCapture={requireLivePhotoOnly}
              onAnswer={handleAnswer}
            />
          ))}
        </div>

        {isCompleted ? (
          <button
            type="button"
            onClick={() => setActiveExecution(null)}
            className="rounded-xl border-2 border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
          >
            Voltar para a lista
          </button>
        ) : (
          <div className="flex gap-2">
            <button
              type="button"
              onClick={() => setActiveExecution(null)}
              className="flex-1 rounded-xl border-2 border-slate-200 px-4 py-2.5 text-sm font-semibold text-slate-700 transition hover:bg-slate-100"
            >
              Voltar (continua em andamento)
            </button>
            <button
              type="button"
              onClick={() => void handleComplete()}
              disabled={isAnswering}
              className="flex-1 rounded-xl bg-emerald-500 px-4 py-2.5 text-sm font-semibold text-white transition hover:bg-emerald-600 disabled:cursor-not-allowed disabled:opacity-50"
            >
              Concluir checklist
            </button>
          </div>
        )}
      </div>
    )
  }

  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-200 bg-slate-50 p-4">
      {errorMessage && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {errorMessage}
        </p>
      )}

      {templatesQuery.isLoading && <p className="text-sm text-slate-400">Carregando…</p>}
      {!templatesQuery.isLoading && templates.length === 0 && (
        <p className="text-sm text-slate-400">Nenhum checklist disponível para este setor agora.</p>
      )}

      {templates.length > 0 && (
        <div className="grid grid-cols-1 gap-4 md:grid-cols-2">
          <KanbanColumn
            title="Pendentes"
            count={pendingTemplates.length}
            emptyLabel="Nenhum checklist pendente."
          >
            {pendingTemplates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                inProgress={findInProgressExecution(template.id)}
                completedToday={wasCompletedToday(template.id)}
                isBusy={isBusy}
                onContinue={setActiveExecution}
                onRequestStart={(t) => onRequestStart(t, suggestedShift(), setActiveExecution)}
              />
            ))}
          </KanbanColumn>
          <KanbanColumn
            title="Concluídos hoje"
            count={completedTemplates.length}
            emptyLabel="Nenhum checklist concluído hoje ainda."
          >
            {completedTemplates.map((template) => (
              <TemplateCard
                key={template.id}
                template={template}
                inProgress={findInProgressExecution(template.id)}
                completedToday={wasCompletedToday(template.id)}
                isBusy={isBusy}
                onContinue={setActiveExecution}
                onRequestStart={(t) => onRequestStart(t, suggestedShift(), setActiveExecution)}
              />
            ))}
          </KanbanColumn>
        </div>
      )}
    </div>
  )
}
