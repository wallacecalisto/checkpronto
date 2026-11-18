import { useEffect, useMemo, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { Toast } from '../../components/Toast'
import { useAudioAlert } from '../../hooks/useAudioAlert'
import { startChecklistExecution } from '../../services/checklistService'
import {
  blockTaskAssignment,
  completeTaskAssignment,
  joinTaskAssignment,
  leaveTaskAssignment,
  resumeTaskAssignment,
  startTaskAssignment,
  uploadTaskAssignmentPhoto,
} from '../../services/taskAssignmentService'
import type { ChecklistExecution, Shift } from '../../types/checklistExecution'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import type { Employee } from '../../types/employee'
import type { Sector } from '../../types/sector'
import { currentDayOfWeek, type TaskAssignment } from '../../types/taskAssignment'
import { InlinePinAuth, type InlinePinAuthPerson } from './InlinePinAuth'
import { SectorChecklistList } from './SectorChecklistList'
import { SectorTaskList } from './SectorTaskList'
import { TaskActionPanel } from './TaskActionPanel'

interface SectorViewProps {
  sector: Sector
  employees: Employee[]
  // Todos os agendamentos OPERACIONAL da loja — filtrados aqui pro setor +
  // dia de hoje.
  assignments: TaskAssignment[]
  shifts: string[]
  checklistsEnabled: boolean
  hideTaskTimer: boolean
  requireLivePhotoOnly: boolean
  autoLogoutMinutes: number
  enableAudioAlerts: boolean
  onBack: () => void
}

type OperationalTab = 'tasks' | 'checklists'

type PendingAuth = {
  title: string
  people: InlinePinAuthPerson[]
  onAuthenticate: (person: InlinePinAuthPerson, pin: string) => Promise<void>
} | null

type ActiveAction = {
  assignment: TaskAssignment
  person: InlinePinAuthPerson
  pin: string
} | null

export function SectorView({
  sector,
  employees,
  assignments,
  shifts,
  checklistsEnabled,
  hideTaskTimer,
  requireLivePhotoOnly,
  autoLogoutMinutes,
  enableAudioAlerts,
  onBack,
}: SectorViewProps) {
  const queryClient = useQueryClient()
  const { playSuccess, playWarning } = useAudioAlert(enableAudioAlerts)
  const [activeTab, setActiveTab] = useState<OperationalTab>('tasks')
  const [pendingAuth, setPendingAuth] = useState<PendingAuth>(null)
  const [activeAction, setActiveAction] = useState<ActiveAction>(null)
  const [toastMessage, setToastMessage] = useState<string | null>(null)
  const [selectedShift, setSelectedShift] = useState(shifts[0] ?? 'Geral')

  useEffect(() => {
    if (!shifts.includes(selectedShift)) {
      setSelectedShift(shifts[0] ?? 'Geral')
    }
  }, [shifts, selectedShift])

  useEffect(() => {
    if (!autoLogoutMinutes || autoLogoutMinutes <= 0) return

    let timeoutId: ReturnType<typeof setTimeout>
    function resetTimer(): void {
      clearTimeout(timeoutId)
      timeoutId = setTimeout(onBack, autoLogoutMinutes * 60 * 1000)
    }

    resetTimer()
    window.addEventListener('click', resetTimer)
    window.addEventListener('keydown', resetTimer)
    window.addEventListener('touchstart', resetTimer)
    return () => {
      clearTimeout(timeoutId)
      window.removeEventListener('click', resetTimer)
      window.removeEventListener('keydown', resetTimer)
      window.removeEventListener('touchstart', resetTimer)
    }
  }, [autoLogoutMinutes, onBack])

  const sectorPeople = useMemo<InlinePinAuthPerson[]>(
    () =>
      employees
        .filter((employee) => employee.sector_id === sector.id)
        .map((employee) => ({ id: employee.id, name: employee.name, hasPin: employee.has_pin })),
    [employees, sector.id],
  )

  const today = currentDayOfWeek()
  const todaysAssignments = useMemo(
    () =>
      assignments.filter(
        (assignment) =>
          assignment.sector_id === sector.id &&
          assignment.day_of_week === today &&
          assignment.shift === selectedShift,
      ),
    [assignments, sector.id, today, selectedShift],
  )

  async function refreshAssignments(): Promise<void> {
    await queryClient.invalidateQueries({ queryKey: ['task-assignments', 'operational'] })
  }

  function closeAuth(): void {
    setPendingAuth(null)
  }

  function handleStartOrJoin(assignment: TaskAssignment): void {
    setPendingAuth({
      title: `Iniciar / Entrar em "${assignment.task_title}"`,
      people: sectorPeople,
      onAuthenticate: async (person, pin) => {
        if (assignment.status === 'PENDING') {
          await startTaskAssignment(assignment.id, { employee_id: person.id, pin })
          await refreshAssignments()
          setToastMessage('Tarefa iniciada.')
          return
        }

        const alreadyActive = assignment.active_participants.some(
          (participant) => participant.employee_id === person.id,
        )
        if (alreadyActive) {
          await refreshAssignments()
          setActiveAction({ assignment, person, pin })
          return
        }

        await joinTaskAssignment(assignment.id, { employee_id: person.id, pin })
        await refreshAssignments()
        setToastMessage('Você entrou na tarefa.')
      },
    })
  }

  async function handlePanelComplete(photoFiles: File[]): Promise<void> {
    if (!activeAction) return
    const { assignment, person, pin } = activeAction
    const photoUrls: string[] = []
    for (const photoFile of photoFiles) {
      const uploadResult = await uploadTaskAssignmentPhoto(assignment.id, {
        employee_id: person.id,
        pin,
        photo: photoFile,
      })
      photoUrls.push(uploadResult.photo_url)
    }
    await completeTaskAssignment(assignment.id, {
      employee_id: person.id,
      pin,
      result: 'FEITO',
      photo_url: photoUrls[0],
      extra_photo_urls: photoUrls.slice(1),
    })
    playSuccess()
    await refreshAssignments()
    setActiveAction(null)
  }

  async function handlePanelLeave(): Promise<void> {
    if (!activeAction) return
    const { assignment, person, pin } = activeAction
    await leaveTaskAssignment(assignment.id, { employee_id: person.id, pin })
    await refreshAssignments()
    setActiveAction(null)
  }

  async function handlePanelBlock(reason: string): Promise<void> {
    if (!activeAction) return
    const { assignment, person, pin } = activeAction
    await blockTaskAssignment(assignment.id, { employee_id: person.id, pin, reason })
    await refreshAssignments()
    setActiveAction(null)
  }

  function handleResume(assignment: TaskAssignment): void {
    setPendingAuth({
      title: `Retomar "${assignment.task_title}"`,
      people: sectorPeople,
      onAuthenticate: async (person, pin) => {
        await resumeTaskAssignment(assignment.id, { employee_id: person.id, pin })
        await refreshAssignments()
      },
    })
  }

  function handleRequestStartChecklist(
    template: ChecklistTemplate,
    shift: Shift,
    onStarted: (execution: ChecklistExecution) => void,
  ): void {
    setPendingAuth({
      title: `Iniciar "${template.name}"`,
      people: sectorPeople,
      onAuthenticate: async (person, pin) => {
        const execution = await startChecklistExecution({
          template_id: template.id,
          shift,
          employee_id: person.id,
          pin,
        })
        onStarted(execution)
      },
    })
  }

  return (
    <div className="flex flex-col gap-4">
      <div className="flex items-center gap-3">
        <button
          type="button"
          onClick={onBack}
          aria-label="Voltar para os setores"
          className="rounded-full border border-slate-200 p-2 text-slate-500 transition-all duration-300 ease-in-out hover:bg-slate-100"
        >
          ←
        </button>
        <h2 className="text-xl font-semibold text-slate-800">{sector.name}</h2>
      </div>

      <div className="flex flex-wrap gap-1.5 rounded-xl bg-slate-100 p-1">
        {shifts.map((shiftOption) => (
          <button
            key={shiftOption}
            type="button"
            onClick={() => setSelectedShift(shiftOption)}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-300 ease-in-out ${
              selectedShift === shiftOption
                ? 'bg-white text-slate-800 shadow-sm'
                : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            {shiftOption}
          </button>
        ))}
      </div>

      {checklistsEnabled && (
        <div className="flex gap-1.5 rounded-xl bg-slate-100 p-1">
          <button
            type="button"
            onClick={() => setActiveTab('tasks')}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-300 ease-in-out ${
              activeTab === 'tasks' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Tarefas
          </button>
          <button
            type="button"
            onClick={() => setActiveTab('checklists')}
            className={`flex-1 rounded-lg py-2 text-sm font-medium transition-all duration-300 ease-in-out ${
              activeTab === 'checklists' ? 'bg-white text-slate-800 shadow-sm' : 'text-slate-500 hover:text-slate-700'
            }`}
          >
            Checklists
          </button>
        </div>
      )}

      {(!checklistsEnabled || activeTab === 'tasks') && (
        <SectorTaskList
          assignments={todaysAssignments}
          isBusy={pendingAuth !== null || activeAction !== null}
          hideTaskTimer={hideTaskTimer}
          onStartOrJoin={handleStartOrJoin}
          onResume={handleResume}
          onOverdue={playWarning}
        />
      )}

      {checklistsEnabled && activeTab === 'checklists' && (
        <SectorChecklistList
          sectorId={sector.id}
          sectorShift={selectedShift}
          isBusy={pendingAuth !== null}
          requireLivePhotoOnly={requireLivePhotoOnly}
          onRequestStart={handleRequestStartChecklist}
        />
      )}

      {pendingAuth && (
        <InlinePinAuth
          title={pendingAuth.title}
          people={pendingAuth.people}
          onAuthenticate={pendingAuth.onAuthenticate}
          onSuccess={closeAuth}
          onCancel={closeAuth}
        />
      )}

      {activeAction && (
        <TaskActionPanel
          assignment={activeAction.assignment}
          person={activeAction.person}
          requireLivePhotoOnly={requireLivePhotoOnly}
          onComplete={handlePanelComplete}
          onLeave={handlePanelLeave}
          onBlock={handlePanelBlock}
          onClose={() => setActiveAction(null)}
        />
      )}

      {toastMessage && <Toast message={toastMessage} onDismiss={() => setToastMessage(null)} />}
    </div>
  )
}
