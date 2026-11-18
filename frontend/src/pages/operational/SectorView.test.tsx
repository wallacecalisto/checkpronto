import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChecklistExecution } from '../../types/checklistExecution'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import type { Employee } from '../../types/employee'
import type { Sector } from '../../types/sector'
import { currentDayOfWeek, type TaskAssignment } from '../../types/taskAssignment'
import { SectorView } from './SectorView'

const mockStartTaskAssignment = vi.fn()
const mockJoinTaskAssignment = vi.fn()
const mockLeaveTaskAssignment = vi.fn()
const mockCompleteTaskAssignment = vi.fn()
const mockBlockTaskAssignment = vi.fn()
const mockResumeTaskAssignment = vi.fn()
const mockUploadTaskAssignmentPhoto = vi.fn()

vi.mock('../../services/taskAssignmentService', () => ({
  startTaskAssignment: (...args: unknown[]) => mockStartTaskAssignment(...args),
  joinTaskAssignment: (...args: unknown[]) => mockJoinTaskAssignment(...args),
  leaveTaskAssignment: (...args: unknown[]) => mockLeaveTaskAssignment(...args),
  completeTaskAssignment: (...args: unknown[]) => mockCompleteTaskAssignment(...args),
  blockTaskAssignment: (...args: unknown[]) => mockBlockTaskAssignment(...args),
  resumeTaskAssignment: (...args: unknown[]) => mockResumeTaskAssignment(...args),
  uploadTaskAssignmentPhoto: (...args: unknown[]) => mockUploadTaskAssignmentPhoto(...args),
}))

const mockStartChecklistExecution = vi.fn()
const mockAnswerChecklistItem = vi.fn()
const mockCompleteChecklistExecution = vi.fn()
const mockListChecklistExecutions = vi.fn()
const mockUploadChecklistItemPhoto = vi.fn()

vi.mock('../../services/checklistService', () => ({
  startChecklistExecution: (...args: unknown[]) => mockStartChecklistExecution(...args),
  answerChecklistItem: (...args: unknown[]) => mockAnswerChecklistItem(...args),
  completeChecklistExecution: (...args: unknown[]) => mockCompleteChecklistExecution(...args),
  listChecklistExecutions: (...args: unknown[]) => mockListChecklistExecutions(...args),
  uploadChecklistItemPhoto: (...args: unknown[]) => mockUploadChecklistItemPhoto(...args),
}))

const mockListChecklistTemplates = vi.fn()

vi.mock('../../services/checklistTemplateService', () => ({
  listChecklistTemplates: (...args: unknown[]) => mockListChecklistTemplates(...args),
}))

const mockSetupPin = vi.fn()

vi.mock('../../services/employeeService', () => ({
  setupPin: (...args: unknown[]) => mockSetupPin(...args),
}))

const mockPlaySuccess = vi.fn()
const mockPlayWarning = vi.fn()

vi.mock('../../hooks/useAudioAlert', () => ({
  useAudioAlert: () => ({ playSuccess: mockPlaySuccess, playWarning: mockPlayWarning }),
}))

const cozinha: Sector = { id: 1, store_id: 1, name: 'Cozinha Quente', active: true }
const outroSetor: Sector = { id: 2, store_id: 1, name: 'Sushi', active: true }

const carlos: Employee = { id: 7, store_id: 1, sector_id: cozinha.id, name: 'Carlos', role_title: null, active: true, has_pin: true }
const bruna: Employee = { id: 8, store_id: 1, sector_id: cozinha.id, name: 'Bruna', role_title: null, active: true, has_pin: true }
const forasteiro: Employee = {
  id: 9,
  store_id: 1,
  sector_id: outroSetor.id,
  name: 'Forasteiro',
  role_title: null,
  active: true,
  has_pin: true,
}
const employees = [carlos, bruna, forasteiro]

const today = currentDayOfWeek()

const pendingAssignment: TaskAssignment = {
  id: 101,
  task_id: 1,
  store_id: 1,
  day_of_week: today,
  task_title: 'Repor estoque',
  task_description: null,
  estimated_duration_minutes: null,
  requires_photo_proof: false,
  shift: 'Manhã',
  sector_id: cozinha.id,
  sector_name: cozinha.name,
  status: 'PENDING',
  started_at: null,
  completed_at: null,
  started_by_employee_id: null,
  completed_by_employee_id: null,
  started_by_user_id: null,
  completed_by_user_id: null,
  result: null,
  justification: null,
  observation: null,
  photo_url: null,
  extra_photo_urls: [],
  elapsed_seconds: null,
  active_participants: [],
  blocked_at: null,
  block_reason: null,
  blocked_by_employee_id: null,
  latest_execution_history_id: null,
}

const inProgressAssignment: TaskAssignment = {
  ...pendingAssignment,
  id: 102,
  task_title: 'Fritar 200 empanados',
  status: 'IN_PROGRESS',
  started_at: '2026-01-01T12:00:00Z',
  started_by_employee_id: carlos.id,
  elapsed_seconds: 30,
  active_participants: [{ employee_id: carlos.id, employee_name: 'Carlos', started_at: '2026-01-01T12:00:00Z' }],
}

const blockedAssignment: TaskAssignment = {
  ...pendingAssignment,
  id: 103,
  task_title: 'Descongelar camarão',
  status: 'BLOCKED',
  started_at: '2026-01-01T12:00:00Z',
  blocked_at: '2026-01-01T12:05:00Z',
  block_reason: 'Faltou camarão no estoque.',
  blocked_by_employee_id: carlos.id,
}

const completedAssignment: TaskAssignment = {
  ...pendingAssignment,
  id: 104,
  task_title: 'Lavar louça',
  status: 'COMPLETED',
  started_at: '2026-01-01T11:00:00Z',
  completed_at: '2026-01-01T11:30:00Z',
  result: 'FEITO',
}

const template: ChecklistTemplate = {
  id: 1,
  store_id: 1,
  name: 'Abertura da Cozinha',
  active: true,
  created_by_user_id: 1,
  target_sector_id: cozinha.id,
  shift: 'Manhã',
  created_at: '2026-01-01T00:00:00Z',
  items: [],
}

const execution: ChecklistExecution = {
  id: 1,
  template_id: template.id,
  template_name: template.name,
  store_id: 1,
  shift: 'MANHA',
  executed_by_user_id: null,
  executed_by_employee_id: carlos.id,
  executed_by_name: 'Carlos',
  validated_by_names: [],
  started_at: '2026-01-01T08:00:00Z',
  finished_at: null,
  status: 'IN_PROGRESS',
  fully_validated: false,
  items: [
    {
      id: 1,
      checklist_execution_id: 1,
      template_item_id: 1,
      item_description_snapshot: 'Ligar a coifa',
      response: null,
      observation: null,
      photo_url: null,
      extra_photo_urls: [],
      requires_photo: false,
      validation: null,
    },
  ],
}

const executionWithPhotoItem: ChecklistExecution = {
  ...execution,
  items: [
    {
      id: 2,
      checklist_execution_id: 1,
      template_item_id: 2,
      item_description_snapshot: 'Fotografar a câmara fria',
      response: null,
      observation: null,
      photo_url: null,
      extra_photo_urls: [],
      requires_photo: true,
      validation: null,
    },
  ],
}

function renderSectorView(
  assignments: TaskAssignment[],
  options: {
    checklistsEnabled?: boolean
    hideTaskTimer?: boolean
    requireLivePhotoOnly?: boolean
    autoLogoutMinutes?: number
    shifts?: string[]
    enableAudioAlerts?: boolean
    onBack?: () => void
  } = {},
) {
  const queryClient = new QueryClient()
  const onBack = options.onBack ?? vi.fn()
  render(
    <QueryClientProvider client={queryClient}>
      <SectorView
        sector={cozinha}
        employees={employees}
        assignments={assignments}
        shifts={options.shifts ?? ['Manhã']}
        checklistsEnabled={options.checklistsEnabled ?? true}
        hideTaskTimer={options.hideTaskTimer ?? false}
        requireLivePhotoOnly={options.requireLivePhotoOnly ?? false}
        autoLogoutMinutes={options.autoLogoutMinutes ?? 5}
        enableAudioAlerts={options.enableAudioAlerts ?? false}
        onBack={onBack}
      />
    </QueryClientProvider>,
  )
  return { onBack }
}

async function typePin(user: ReturnType<typeof userEvent.setup>, pin: string) {
  for (const digit of pin) {
    await user.click(screen.getByRole('button', { name: digit }))
  }
}

describe('SectorView', () => {
  beforeEach(() => {
    mockStartTaskAssignment.mockReset()
    mockJoinTaskAssignment.mockReset()
    mockLeaveTaskAssignment.mockReset()
    mockCompleteTaskAssignment.mockReset()
    mockBlockTaskAssignment.mockReset()
    mockResumeTaskAssignment.mockReset()
    mockUploadTaskAssignmentPhoto.mockReset()
    mockStartChecklistExecution.mockReset()
    mockAnswerChecklistItem.mockReset()
    mockCompleteChecklistExecution.mockReset()
    mockUploadChecklistItemPhoto.mockReset()
    mockListChecklistExecutions.mockReset().mockResolvedValue([])
    mockListChecklistTemplates.mockReset().mockResolvedValue([])
    mockSetupPin.mockReset()
    mockPlaySuccess.mockReset()
    mockPlayWarning.mockReset()
  })

  it('mostra só as tarefas de HOJE deste setor (não de outros setores)', async () => {
    const otherSectorAssignment: TaskAssignment = { ...pendingAssignment, id: 999, sector_id: outroSetor.id }
    renderSectorView([pendingAssignment, otherSectorAssignment])

    expect(await screen.findByText('Repor estoque')).toBeInTheDocument()
    expect(screen.queryAllByText('Repor estoque')).toHaveLength(1)
  })

  it('tarefa de outro turno não aparece de jeito nenhum, mesmo hoje e no setor certo', async () => {
    const nightAssignment: TaskAssignment = { ...pendingAssignment, id: 999, task_title: 'Fechar o caixa', shift: 'Noite' }
    renderSectorView([pendingAssignment, nightAssignment], { shifts: ['Manhã', 'Noite'] })

    expect(await screen.findByText('Repor estoque')).toBeInTheDocument()
    expect(screen.queryByText('Fechar o caixa')).not.toBeInTheDocument()

    await userEvent.setup().click(screen.getByRole('button', { name: 'Noite' }))

    expect(await screen.findByText('Fechar o caixa')).toBeInTheDocument()
    expect(screen.queryByText('Repor estoque')).not.toBeInTheDocument()
  })

  it('checklist de outro turno não aparece nas colunas, mesmo turno errado selecionado', async () => {
    const nightTemplate: ChecklistTemplate = { ...template, id: 2, name: 'Fechamento Noturno', shift: 'Noite' }
    mockListChecklistTemplates.mockResolvedValue([template, nightTemplate])
    const user = userEvent.setup()
    renderSectorView([], { shifts: ['Manhã', 'Noite'] })

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    expect(await screen.findByText('Abertura da Cozinha')).toBeInTheDocument()
    expect(screen.queryByText('Fechamento Noturno')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Noite' }))

    expect(await screen.findByText('Fechamento Noturno')).toBeInTheDocument()
    expect(screen.queryByText('Abertura da Cozinha')).not.toBeInTheDocument()
  })

  it('tarefas se distribuem em 3 colunas, e impedidas ficam em Pendentes', async () => {
    renderSectorView([pendingAssignment, inProgressAssignment, blockedAssignment, completedAssignment])

    await screen.findByText('Repor estoque')

    const pendingColumn = screen.getByText('Pendentes').closest('div')!.parentElement!
    const inProgressColumn = screen.getByText('Em Andamento').closest('div')!.parentElement!
    const completedColumn = screen.getByText('Concluídas').closest('div')!.parentElement!

    // Pendente de verdade E impedida (destacada em laranja) caem na mesma coluna.
    expect(within(pendingColumn).getByText('Repor estoque')).toBeInTheDocument()
    expect(within(pendingColumn).getByText('Descongelar camarão')).toBeInTheDocument()
    expect(within(pendingColumn).queryByText('Fritar 200 empanados')).not.toBeInTheDocument()
    expect(within(pendingColumn).queryByText('Lavar louça')).not.toBeInTheDocument()

    expect(within(inProgressColumn).getByText('Fritar 200 empanados')).toBeInTheDocument()
    expect(within(completedColumn).getByText('Lavar louça')).toBeInTheDocument()
  })

  it('tarefa em andamento sem ninguém ativo ganha destaque "Parada / Sem responsável"', async () => {
    const abandonedAssignment: TaskAssignment = { ...inProgressAssignment, active_participants: [] }
    renderSectorView([abandonedAssignment])

    await screen.findByText('Fritar 200 empanados')
    expect(screen.getByText('Parada / Sem responsável')).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Iniciar Tarefa' })).toBeInTheDocument()
  })

  it('tarefa em andamento COM alguém ativo não mostra o destaque de abandonada', async () => {
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    expect(screen.queryByText('Parada / Sem responsável')).not.toBeInTheDocument()
  })


  it('Iniciar Tarefa (PENDING): só oferece funcionários DESTE setor e chama startTaskAssignment', async () => {
    mockStartTaskAssignment.mockResolvedValueOnce({ ...pendingAssignment, status: 'IN_PROGRESS' })
    const user = userEvent.setup()
    renderSectorView([pendingAssignment])

    await user.click(await screen.findByRole('button', { name: 'Iniciar Tarefa' }))

    expect(screen.getByRole('button', { name: 'Carlos' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Bruna' })).toBeInTheDocument()
    expect(screen.queryByText('Forasteiro')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Bruna' }))
    await typePin(user, '1234')

    await waitFor(() => {
      expect(mockStartTaskAssignment).toHaveBeenCalledWith(pendingAssignment.id, { employee_id: bruna.id, pin: '1234' })
    })
  })

  it('iniciar uma tarefa PENDING mostra um toast e devolve pro Kanban, sem abrir o painel de ações', async () => {
    mockStartTaskAssignment.mockResolvedValueOnce({ ...pendingAssignment, status: 'IN_PROGRESS' })
    const user = userEvent.setup()
    renderSectorView([pendingAssignment])

    await user.click(await screen.findByRole('button', { name: 'Iniciar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Bruna' }))
    await typePin(user, '1234')

    expect(await screen.findByText('Tarefa iniciada.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Concluir' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sair da Tarefa' })).not.toBeInTheDocument()
    expect(mockCompleteTaskAssignment).not.toHaveBeenCalled()
  })

  it('Entrar na Tarefa (IN_PROGRESS por outro): chama joinTaskAssignment', async () => {
    mockJoinTaskAssignment.mockResolvedValueOnce({ ...inProgressAssignment })
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Bruna' }))
    await typePin(user, '2222')

    await waitFor(() => {
      expect(mockJoinTaskAssignment).toHaveBeenCalledWith(inProgressAssignment.id, { employee_id: bruna.id, pin: '2222' })
    })
  })

  it('quem NUNCA esteve na tarefa entra, vê um toast, e o painel de Concluir NÃO abre', async () => {
    mockJoinTaskAssignment.mockResolvedValueOnce({ ...inProgressAssignment })
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Bruna' }))
    await typePin(user, '2222')

    expect(await screen.findByText('Você entrou na tarefa.')).toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Concluir' })).not.toBeInTheDocument()
    expect(screen.queryByRole('button', { name: 'Sair da Tarefa' })).not.toBeInTheDocument()
    expect(mockCompleteTaskAssignment).not.toHaveBeenCalled()
  })

  it('Entrar/Encerrar quando a pessoa já está ativa na tarefa: não chama join de novo, só abre o painel', async () => {
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    expect(await screen.findByRole('button', { name: 'Concluir' })).toBeInTheDocument()
    expect(mockJoinTaskAssignment).not.toHaveBeenCalled()
    expect(mockStartTaskAssignment).not.toHaveBeenCalled()
  })

  it('Painel de ações — Concluir (sem foto exigida): completa direto como FEITO, sem pedir PIN de novo', async () => {
    mockCompleteTaskAssignment.mockResolvedValueOnce({ ...inProgressAssignment, status: 'COMPLETED', result: 'FEITO' })
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    await user.click(await screen.findByRole('button', { name: 'Concluir' }))

    await waitFor(() => {
      expect(mockCompleteTaskAssignment).toHaveBeenCalledWith(inProgressAssignment.id, {
        employee_id: carlos.id,
        pin: '1234',
        result: 'FEITO',
        photo_url: undefined,
        extra_photo_urls: [],
      })
    })
  })

  it('concluir uma tarefa com sucesso toca o beep positivo', async () => {
    mockCompleteTaskAssignment.mockResolvedValueOnce({ ...inProgressAssignment, status: 'COMPLETED', result: 'FEITO' })
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')
    await user.click(await screen.findByRole('button', { name: 'Concluir' }))

    await waitFor(() => expect(mockPlaySuccess).toHaveBeenCalledTimes(1))
    expect(mockPlayWarning).not.toHaveBeenCalled()
  })

  it('tarefa em andamento que já estourou o SLA toca o beep de aviso e fica com o cronômetro laranja', async () => {
    const overdueAssignment = { ...inProgressAssignment, estimated_duration_minutes: 1, elapsed_seconds: 120 }
    renderSectorView([overdueAssignment])

    const elapsedBadge = await screen.findByText('02:00')
    expect(elapsedBadge).toHaveClass('bg-orange-50', 'text-orange-600')
    await waitFor(() => expect(mockPlayWarning).toHaveBeenCalledTimes(1))
    expect(mockPlaySuccess).not.toHaveBeenCalled()
  })

  it('Painel de ações — Concluir com foto obrigatória: bloqueia Confirmar até a foto ser anexada', async () => {
    const assignmentRequiringPhoto = { ...inProgressAssignment, requires_photo_proof: true }
    mockUploadTaskAssignmentPhoto.mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/empanados.jpg' })
    mockCompleteTaskAssignment.mockResolvedValueOnce({ ...assignmentRequiringPhoto, status: 'COMPLETED', result: 'FEITO' })
    const user = userEvent.setup()
    renderSectorView([assignmentRequiringPhoto])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')
    await user.click(await screen.findByRole('button', { name: 'Concluir' }))

    const confirmButton = await screen.findByRole('button', { name: 'Confirmar' })
    expect(confirmButton).toBeDisabled()

    const photoFile = new File(['conteudo'], 'empanados.jpg', { type: 'image/jpeg' })
    await user.upload(screen.getByLabelText(/foto de comprovação/i), photoFile)
    expect(confirmButton).toBeEnabled()
    await user.click(confirmButton)

    await waitFor(() => {
      expect(mockUploadTaskAssignmentPhoto).toHaveBeenCalledWith(assignmentRequiringPhoto.id, {
        employee_id: carlos.id,
        pin: '1234',
        photo: photoFile,
      })
    })
    await waitFor(() => {
      expect(mockCompleteTaskAssignment).toHaveBeenCalledWith(assignmentRequiringPhoto.id, {
        employee_id: carlos.id,
        pin: '1234',
        result: 'FEITO',
        photo_url: 'https://cdn.example.com/empanados.jpg',
        extra_photo_urls: [],
      })
    })
  })

  it('anexar mais de uma foto sobe cada uma, a primeira vira photo_url e o resto extra_photo_urls', async () => {
    const assignmentRequiringPhoto = { ...inProgressAssignment, requires_photo_proof: true }
    mockUploadTaskAssignmentPhoto
      .mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/foto1.jpg' })
      .mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/foto2.jpg' })
    mockCompleteTaskAssignment.mockResolvedValueOnce({ ...assignmentRequiringPhoto, status: 'COMPLETED', result: 'FEITO' })
    const user = userEvent.setup()
    renderSectorView([assignmentRequiringPhoto])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')
    await user.click(await screen.findByRole('button', { name: 'Concluir' }))

    const photoInput = screen.getByLabelText(/foto de comprovação/i)
    const photoFile1 = new File(['conteudo1'], 'foto1.jpg', { type: 'image/jpeg' })
    const photoFile2 = new File(['conteudo2'], 'foto2.jpg', { type: 'image/jpeg' })
    await user.upload(photoInput, [photoFile1, photoFile2])

    expect(screen.getByRole('button', { name: 'Remover foto 1' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Remover foto 2' })).toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(mockCompleteTaskAssignment).toHaveBeenCalledWith(assignmentRequiringPhoto.id, {
        employee_id: carlos.id,
        pin: '1234',
        result: 'FEITO',
        photo_url: 'https://cdn.example.com/foto1.jpg',
        extra_photo_urls: ['https://cdn.example.com/foto2.jpg'],
      })
    })
  })

  it('remover uma foto antes de confirmar tira ela da lista final', async () => {
    const assignmentRequiringPhoto = { ...inProgressAssignment, requires_photo_proof: true }
    mockUploadTaskAssignmentPhoto.mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/foto1.jpg' })
    mockCompleteTaskAssignment.mockResolvedValueOnce({ ...assignmentRequiringPhoto, status: 'COMPLETED', result: 'FEITO' })
    const user = userEvent.setup()
    renderSectorView([assignmentRequiringPhoto])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')
    await user.click(await screen.findByRole('button', { name: 'Concluir' }))

    const photoInput = screen.getByLabelText(/foto de comprovação/i)
    const photoFile1 = new File(['conteudo1'], 'foto1.jpg', { type: 'image/jpeg' })
    const photoFile2 = new File(['conteudo2'], 'foto2.jpg', { type: 'image/jpeg' })
    await user.upload(photoInput, [photoFile1, photoFile2])
    await user.click(screen.getByRole('button', { name: 'Remover foto 2' }))

    expect(screen.queryByRole('button', { name: 'Remover foto 2' })).not.toBeInTheDocument()

    await user.click(await screen.findByRole('button', { name: 'Confirmar' }))

    await waitFor(() => {
      expect(mockUploadTaskAssignmentPhoto).toHaveBeenCalledTimes(1)
      expect(mockCompleteTaskAssignment).toHaveBeenCalledWith(assignmentRequiringPhoto.id, {
        employee_id: carlos.id,
        pin: '1234',
        result: 'FEITO',
        photo_url: 'https://cdn.example.com/foto1.jpg',
        extra_photo_urls: [],
      })
    })
  })

  it('Painel de ações — Sair da Tarefa: libera a vaga com um único toque, sem motivo', async () => {
    mockLeaveTaskAssignment.mockResolvedValueOnce({ ...inProgressAssignment, active_participants: [] })
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    await user.click(await screen.findByRole('button', { name: 'Sair da Tarefa' }))

    await waitFor(() => {
      expect(mockLeaveTaskAssignment).toHaveBeenCalledWith(inProgressAssignment.id, { employee_id: carlos.id, pin: '1234' })
    })
  })

  it('Painel de ações — Reportar Impedimento: motivo obrigatório, sem pedir PIN de novo', async () => {
    mockBlockTaskAssignment.mockResolvedValueOnce({ ...inProgressAssignment, status: 'BLOCKED' })
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    await user.click(await screen.findByRole('button', { name: 'Reportar Impedimento' }))
    const confirmButton = screen.getByRole('button', { name: 'Confirmar' })
    expect(confirmButton).toBeDisabled()

    await user.type(screen.getByLabelText(/motivo do impedimento/i), 'Faltou camarão.')
    expect(confirmButton).toBeEnabled()
    await user.click(confirmButton)

    await waitFor(() => {
      expect(mockBlockTaskAssignment).toHaveBeenCalledWith(inProgressAssignment.id, {
        employee_id: carlos.id,
        pin: '1234',
        reason: 'Faltou camarão.',
      })
    })
  })

  it('Painel de ações — Fechar (✕) sem agir: não chama nenhuma ação, tarefa continua em andamento', async () => {
    const user = userEvent.setup()
    renderSectorView([inProgressAssignment])

    await screen.findByText('Fritar 200 empanados')
    await user.click(screen.getByRole('button', { name: 'Entrar na Tarefa / Encerrar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    await user.click(await screen.findByRole('button', { name: 'Fechar' }))

    expect(screen.queryByRole('button', { name: 'Concluir' })).not.toBeInTheDocument()
    expect(mockCompleteTaskAssignment).not.toHaveBeenCalled()
    expect(mockLeaveTaskAssignment).not.toHaveBeenCalled()
    expect(mockBlockTaskAssignment).not.toHaveBeenCalled()
  })

  it('Retomar: chama resumeTaskAssignment com quem for escolhido', async () => {
    mockResumeTaskAssignment.mockResolvedValueOnce({ ...blockedAssignment, status: 'IN_PROGRESS' })
    const user = userEvent.setup()
    renderSectorView([blockedAssignment])

    await screen.findByText('Descongelar camarão')
    await user.click(screen.getByRole('button', { name: 'Retomar' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    await waitFor(() => {
      expect(mockResumeTaskAssignment).toHaveBeenCalledWith(blockedAssignment.id, { employee_id: carlos.id, pin: '1234' })
    })
  })

  it('PIN errado numa ação não chama a API de ação nenhuma', async () => {
    mockStartTaskAssignment.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'PIN incorreto.', code: 'PIN_INCORRECT' } },
    })
    const user = userEvent.setup()
    renderSectorView([pendingAssignment])

    await user.click(await screen.findByRole('button', { name: 'Iniciar Tarefa' }))
    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '0000')

    expect(await screen.findByRole('alert')).toHaveTextContent('PIN incorreto.')
    expect(mockStartTaskAssignment).toHaveBeenCalledTimes(1)
  })

  it('Responder Checklist: iniciar exige PIN inline; templates sem execução em andamento mostram "Iniciar"', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockStartChecklistExecution.mockResolvedValueOnce(execution)
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Iniciar' }))

    await user.click(screen.getByRole('button', { name: 'Carlos' }))
    await typePin(user, '1234')

    await waitFor(() => {
      expect(mockStartChecklistExecution).toHaveBeenCalledWith({
        template_id: template.id,
        shift: expect.any(String),
        employee_id: carlos.id,
        pin: '1234',
      })
    })
    expect(await screen.findByText('Ligar a coifa')).toBeInTheDocument()
  })

  it('checklist já em andamento mostra "Continuar" e não exige PIN', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockListChecklistExecutions.mockResolvedValue([execution])
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Continuar' }))

    expect(await screen.findByText('Ligar a coifa')).toBeInTheDocument()
    expect(mockStartChecklistExecution).not.toHaveBeenCalled()
  })

  it('template concluído hoje ganha o selo "Concluído hoje" e cai na coluna própria', async () => {
    const templateB: ChecklistTemplate = { ...template, id: 2, name: 'Fechamento da Cozinha' }
    mockListChecklistTemplates.mockResolvedValue([template, templateB])
    mockListChecklistExecutions.mockImplementation((params: { status?: string }) => {
      if (params.status === 'COMPLETED') {
        return Promise.resolve([
          { ...execution, id: 99, template_id: template.id, status: 'COMPLETED', finished_at: new Date().toISOString() },
        ])
      }
      return Promise.resolve([])
    })
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await screen.findByText('Fechamento da Cozinha')

    expect(screen.getByText('Concluído hoje')).toBeInTheDocument()

    const pendingColumn = screen.getByText('Pendentes').closest('div')!.parentElement!
    const completedColumn = screen.getByText('Concluídos hoje').closest('div')!.parentElement!
    // "Abertura da Cozinha" já foi concluída hoje (mock acima) — cai na
    // coluna de concluídos, mesmo tendo sido cadastrada primeiro.
    expect(within(completedColumn).getByText('Abertura da Cozinha')).toBeInTheDocument()
    expect(within(pendingColumn).getByText('Fechamento da Cozinha')).toBeInTheDocument()
    expect(within(pendingColumn).queryByText('Abertura da Cozinha')).not.toBeInTheDocument()
  })

  it('concluído ONTEM aparece em Pendentes hoje, livre pra iniciar de novo', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    const yesterday = new Date()
    yesterday.setDate(yesterday.getDate() - 1)
    mockListChecklistExecutions.mockImplementation((params: { status?: string }) => {
      if (params.status === 'COMPLETED') {
        return Promise.resolve([
          { ...execution, id: 98, template_id: template.id, status: 'COMPLETED', finished_at: yesterday.toISOString() },
        ])
      }
      return Promise.resolve([])
    })
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await screen.findByText('Abertura da Cozinha')

    // Concluído ONTEM não conta como "hoje" — sem selo, e na coluna Pendentes.
    expect(screen.queryByText('Concluído hoje')).not.toBeInTheDocument()
    const pendingColumn = screen.getByText('Pendentes').closest('div')!.parentElement!
    expect(within(pendingColumn).getByText('Abertura da Cozinha')).toBeInTheDocument()
    expect(within(pendingColumn).getByRole('button', { name: 'Iniciar' })).toBeInTheDocument()
  })

  it('item que exige foto bloqueia OK/Divergente até uma foto ser anexada', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockListChecklistExecutions.mockResolvedValue([executionWithPhotoItem])
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Continuar' }))

    await screen.findByText('Fotografar a câmara fria')
    expect(screen.getByRole('button', { name: 'OK' })).toBeDisabled()
    expect(screen.getByRole('button', { name: 'Divergente' })).toBeDisabled()
    expect(screen.getByText('Este item exige uma foto para ser respondido.')).toBeInTheDocument()
  })

  it('com require_live_photo_only ligado, o input do item de checklist força a câmera (capture=environment)', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockListChecklistExecutions.mockResolvedValue([executionWithPhotoItem])
    const user = userEvent.setup()
    renderSectorView([], { requireLivePhotoOnly: true })

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Continuar' }))
    await screen.findByText('Fotografar a câmara fria')

    const photoInput = screen.getByLabelText(/foto de comprovação/i)
    expect(photoInput).toHaveAttribute('capture', 'environment')
  })

  it('com require_live_photo_only desligado (padrão), o input do item de checklist permite escolher da galeria', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockListChecklistExecutions.mockResolvedValue([executionWithPhotoItem])
    const user = userEvent.setup()
    renderSectorView([], { requireLivePhotoOnly: false })

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Continuar' }))
    await screen.findByText('Fotografar a câmara fria')

    const photoInput = screen.getByLabelText(/foto de comprovação/i)
    expect(photoInput).not.toHaveAttribute('capture')
  })

  it('anexar a foto sobe a foto primeiro, depois responde o item com a photo_url retornada', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockListChecklistExecutions.mockResolvedValue([executionWithPhotoItem])
    mockUploadChecklistItemPhoto.mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/camara-fria.jpg' })
    mockAnswerChecklistItem.mockResolvedValueOnce({
      ...executionWithPhotoItem.items[0],
      response: 'OK',
      photo_url: 'https://cdn.example.com/camara-fria.jpg',
    })
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Continuar' }))
    await screen.findByText('Fotografar a câmara fria')

    const photoFile = new File(['conteudo'], 'camara-fria.jpg', { type: 'image/jpeg' })
    const photoInput = screen.getByLabelText(/foto de comprovação/i)
    await user.upload(photoInput, photoFile)

    await user.click(screen.getByRole('button', { name: 'OK' }))

    await waitFor(() => {
      expect(mockUploadChecklistItemPhoto).toHaveBeenCalledWith(executionWithPhotoItem.id, 2, { photo: photoFile })
    })
    await waitFor(() => {
      expect(mockAnswerChecklistItem).toHaveBeenCalledWith(executionWithPhotoItem.id, 2, {
        response: 'OK',
        observation: undefined,
        photo_url: 'https://cdn.example.com/camara-fria.jpg',
        extra_photo_urls: [],
      })
    })
  })

  it('anexar mais de uma foto num item de checklist sobe cada uma, com preview e remoção', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockListChecklistExecutions.mockResolvedValue([executionWithPhotoItem])
    mockUploadChecklistItemPhoto
      .mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/foto1.jpg' })
      .mockResolvedValueOnce({ photo_url: 'https://cdn.example.com/foto2.jpg' })
    mockAnswerChecklistItem.mockResolvedValueOnce({
      ...executionWithPhotoItem.items[0],
      response: 'OK',
      photo_url: 'https://cdn.example.com/foto1.jpg',
      extra_photo_urls: ['https://cdn.example.com/foto2.jpg'],
    })
    const user = userEvent.setup()
    renderSectorView([])

    await user.click(await screen.findByRole('button', { name: 'Checklists' }))
    await user.click(await screen.findByRole('button', { name: 'Continuar' }))
    await screen.findByText('Fotografar a câmara fria')

    const photoInput = screen.getByLabelText(/foto de comprovação/i)
    const photoFile1 = new File(['conteudo1'], 'foto1.jpg', { type: 'image/jpeg' })
    const photoFile2 = new File(['conteudo2'], 'foto2.jpg', { type: 'image/jpeg' })
    const photoFile3 = new File(['conteudo3'], 'foto3.jpg', { type: 'image/jpeg' })
    await user.upload(photoInput, [photoFile1, photoFile2, photoFile3])
    // Desiste da terceira foto antes de confirmar.
    await user.click(screen.getByRole('button', { name: 'Remover foto 3' }))

    await user.click(screen.getByRole('button', { name: 'OK' }))

    await waitFor(() => {
      expect(mockUploadChecklistItemPhoto).toHaveBeenCalledTimes(2)
    })
    await waitFor(() => {
      expect(mockAnswerChecklistItem).toHaveBeenCalledWith(executionWithPhotoItem.id, 2, {
        response: 'OK',
        observation: undefined,
        photo_url: 'https://cdn.example.com/foto1.jpg',
        extra_photo_urls: ['https://cdn.example.com/foto2.jpg'],
      })
    })
  })

  it('sem operational_checklists_enabled, a aba de Checklists nem aparece', async () => {
    renderSectorView([pendingAssignment], { checklistsEnabled: false })

    await screen.findByText('Repor estoque')
    expect(screen.queryByRole('button', { name: 'Checklists' })).not.toBeInTheDocument()
  })

  it('"Voltar para os setores" chama onBack', async () => {
    const user = userEvent.setup()
    const { onBack } = renderSectorView([pendingAssignment])

    await user.click(await screen.findByRole('button', { name: 'Voltar para os setores' }))

    expect(onBack).toHaveBeenCalled()
  })
})

describe('SectorView — auto-logout por inatividade', () => {
  beforeEach(() => {
    mockListChecklistExecutions.mockReset().mockResolvedValue([])
    mockListChecklistTemplates.mockReset().mockResolvedValue([])
    vi.useFakeTimers({ shouldAdvanceTime: true })
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('volta pra grade de setores sozinho depois de N minutos sem interação', async () => {
    const { onBack } = renderSectorView([pendingAssignment], { autoLogoutMinutes: 1 })

    await screen.findByText('Repor estoque')
    vi.advanceTimersByTime(60 * 1000)

    expect(onBack).toHaveBeenCalled()
  })

  it('qualquer interação reinicia a contagem', async () => {
    const user = userEvent.setup({ advanceTimers: vi.advanceTimersByTime })
    const { onBack } = renderSectorView([pendingAssignment], { autoLogoutMinutes: 1 })

    await screen.findByText('Repor estoque')
    vi.advanceTimersByTime(50 * 1000)
    await user.click(screen.getByText('Repor estoque'))
    vi.advanceTimersByTime(50 * 1000)

    expect(onBack).not.toHaveBeenCalled()
  })
})
