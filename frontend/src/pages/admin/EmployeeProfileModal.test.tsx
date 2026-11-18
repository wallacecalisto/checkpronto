import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { EmployeeProfile } from '../../types/dashboard'
import { EmployeeProfileModal } from './EmployeeProfileModal'

const mockGetEmployeeProfile = vi.fn()
const mockGetExecutionTimeline = vi.fn()

vi.mock('../../services/dashboardService', () => ({
  getEmployeeProfile: (...args: unknown[]) => mockGetEmployeeProfile(...args),
}))

vi.mock('../../services/taskExecutionHistoryService', () => ({
  getExecutionTimeline: (...args: unknown[]) => mockGetExecutionTimeline(...args),
}))

const profileWithSla: EmployeeProfile = {
  employee_id: 1,
  employee_name: 'Ana Souza',
  completed_count: 8,
  avg_execution_seconds: 4320,
  on_time_count: 6,
  late_count: 2,
  on_time_rate: 75,
  tasks: [
    {
      id: 101,
      task_title: 'Lavar louça',
      started_at: '2026-09-10T13:00:00Z',
      completed_at: '2026-09-10T14:00:00Z',
      result: 'FEITO',
      estimated_duration_minutes: 30,
      duration_seconds: 1800,
      on_time: true,
      justification: null,
      observation: null,
      photo_url: null,
    },
    {
      id: 102,
      task_title: 'Organizar estoque',
      started_at: '2026-09-10T15:00:00Z',
      completed_at: '2026-09-10T16:30:00Z',
      result: 'FEITO',
      estimated_duration_minutes: 30,
      duration_seconds: 5400,
      on_time: false,
      justification: null,
      observation: null,
      photo_url: null,
    },
  ],
}

// mesma tarefa concluída duas vezes no período — o mínimo pra
// "Evolução do tempo de execução por tarefa" ter o que desenhar num gráfico.
const profileWithEvolution: EmployeeProfile = {
  employee_id: 1,
  employee_name: 'Ana Souza',
  completed_count: 2,
  avg_execution_seconds: 2100,
  on_time_count: 1,
  late_count: 1,
  on_time_rate: 50,
  tasks: [
    {
      id: 201,
      task_title: 'Lavar louça',
      started_at: '2026-09-08T13:00:00Z',
      completed_at: '2026-09-08T13:25:00Z',
      result: 'FEITO',
      estimated_duration_minutes: 30,
      duration_seconds: 1500,
      on_time: true,
      justification: null,
      observation: null,
      photo_url: null,
    },
    {
      id: 202,
      task_title: 'Lavar louça',
      started_at: '2026-09-10T13:00:00Z',
      completed_at: '2026-09-10T13:45:00Z',
      result: 'FEITO',
      estimated_duration_minutes: 30,
      duration_seconds: 2700,
      on_time: false,
      justification: null,
      observation: null,
      photo_url: null,
    },
  ],
}

function renderModal(props: Partial<Parameters<typeof EmployeeProfileModal>[0]> = {}) {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <EmployeeProfileModal employeeId={1} employeeName="Ana Souza" onClose={vi.fn()} {...props} />
    </QueryClientProvider>,
  )
}

describe('EmployeeProfileModal', () => {
  beforeEach(() => {
    mockGetEmployeeProfile.mockReset()
    mockGetExecutionTimeline.mockReset()
  })

  it('"Ver detalhes" abre o modal de timeline da execução', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithSla)
    mockGetExecutionTimeline.mockResolvedValue({
      execution_group_id: 'x',
      task_id: 1,
      task_title: 'Lavar louça',
      created_by_user_name: 'Gestora',
      estimated_duration_minutes: 30,
      started_at: '2026-09-10T13:00:00Z',
      completed_at: '2026-09-10T14:00:00Z',
      total_elapsed_seconds: 3600,
      result: 'FEITO',
      justification: null,
      observation: null,
      participants: [{ employee_id: 1, employee_name: 'Ana Souza', worked_duration_seconds: 1800 }],
      sessions: [],
      blocks: [],
    })
    const user = userEvent.setup()
    renderModal()

    await user.click((await screen.findAllByRole('button', { name: 'Ver detalhes' }))[0])

    expect(await screen.findByText('Detalhes da Execução')).toBeInTheDocument()
    expect(mockGetExecutionTimeline).toHaveBeenCalledWith(101)
  })

  it('mostra o nome do funcionário no título do modal', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithSla)
    renderModal()

    expect(await screen.findByText('Raio-X — Ana Souza')).toBeInTheDocument()
  })

  it('mostra os três blocos de estatísticas com os valores do perfil', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithSla)
    renderModal()

    expect(await screen.findByText('Concluídas')).toBeInTheDocument()
    expect(screen.getByText('8')).toBeInTheDocument()

    expect(screen.getByText('Tempo médio')).toBeInTheDocument()
    expect(screen.getByText('1h 12min')).toBeInTheDocument()

    // "No prazo" também aparece como badge por tarefa na lista abaixo — o
    // rótulo do bloco de estatística é o único que fica num <p>.
    const statLabel = screen.getAllByText('No prazo').find((element) => element.tagName === 'P')
    expect(statLabel).toBeDefined()
    expect(screen.getByText('75%')).toBeInTheDocument()
  })

  it('mostra os badges de no prazo/com atraso quando on_time_rate não é nulo', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithSla)
    renderModal()

    expect(await screen.findByText('6 no prazo')).toBeInTheDocument()
    expect(screen.getByText('2 com atraso')).toBeInTheDocument()
  })

  it('esconde os badges de no prazo/com atraso quando on_time_rate é nulo (sem SLA)', async () => {
    mockGetEmployeeProfile.mockResolvedValue({
      ...profileWithSla,
      on_time_count: 0,
      late_count: 0,
      on_time_rate: null,
      tasks: [],
    })
    renderModal()

    expect(await screen.findByText('Concluídas')).toBeInTheDocument()
    // O próprio bloco "No prazo" continua aparecendo (com "—" no lugar do
    // percentual) — só os badges de contagem (ex.: "6 no prazo") somem.
    expect(screen.getAllByText('—').length).toBeGreaterThan(0)
    expect(screen.queryByText(/no prazo$/)).not.toBeInTheDocument()
    expect(screen.queryByText(/com atraso$/)).not.toBeInTheDocument()
  })

  it('lista as tarefas concluídas com o badge de no prazo/com atraso de cada uma', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithSla)
    renderModal()

    // o título da tarefa também aparece como <option> no seletor
    // de evolução — o card da lista é sempre o que está num <p>.
    await screen.findByText('Concluídas')
    const louca = screen.getAllByText('Lavar louça').find((element) => element.tagName === 'P')
    expect(louca).toBeDefined()
    const loucaCard = (louca as HTMLElement).closest('div')
    expect(loucaCard).not.toBeNull()
    expect(within(loucaCard as HTMLElement).getByText('No prazo')).toBeInTheDocument()

    const estoque = screen.getAllByText('Organizar estoque').find((element) => element.tagName === 'P')
    expect(estoque).toBeDefined()
    const estoqueCard = (estoque as HTMLElement).closest('div')
    expect(estoqueCard).not.toBeNull()
    expect(within(estoqueCard as HTMLElement).getByText('Com atraso')).toBeInTheDocument()
  })

  it('selecionar uma tarefa com 2+ conclusões no seletor de evolução mostra o gráfico', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithEvolution)
    const user = userEvent.setup()
    renderModal()

    const select = await screen.findByLabelText('Evolução do tempo de execução por tarefa')
    expect(within(select).getByRole('option', { name: 'Lavar louça' })).toBeInTheDocument()

    await user.selectOptions(select, 'Lavar louça')

    expect(
      screen.queryByText(/sem histórico suficiente para um gráfico/i),
    ).not.toBeInTheDocument()
  })

  it('selecionar uma tarefa com só 1 conclusão mostra a mensagem de "sem histórico suficiente"', async () => {
    mockGetEmployeeProfile.mockResolvedValue(profileWithSla)
    const user = userEvent.setup()
    renderModal()

    const select = await screen.findByLabelText('Evolução do tempo de execução por tarefa')
    await user.selectOptions(select, 'Lavar louça')

    expect(await screen.findByText(/sem histórico suficiente para um gráfico/i)).toBeInTheDocument()
  })

  it('mostra a justificativa/observação de uma tarefa quando presente', async () => {
    mockGetEmployeeProfile.mockResolvedValue({
      ...profileWithSla,
      tasks: [
        {
          task_title: 'Limpar fritadeira',
          started_at: '2026-09-10T13:00:00Z',
          completed_at: '2026-09-10T14:00:00Z',
          result: 'NAO_FEITO',
          estimated_duration_minutes: 30,
          duration_seconds: 1800,
          on_time: false,
          justification: 'Fritadeira quebrada.',
          observation: null,
        },
      ],
    })
    renderModal()

    expect(await screen.findByText(/Fritadeira quebrada/)).toBeInTheDocument()
  })
})
