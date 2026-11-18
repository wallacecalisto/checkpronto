import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SelectedStoreProvider } from '../../contexts/SelectedStoreContext'
import type { User } from '../../types/auth'
import type {
  DashboardSummary,
  EmployeeProfile,
  EmployeeRankingEntry,
  ExceptionEntry,
  RecentChecklistEntry,
  WeeklyTrendPoint,
} from '../../types/dashboard'
import type { TaskAssignment } from '../../types/taskAssignment'
import { AdminDashboardPage } from './Dashboard'

const mockGetDashboardSummary = vi.fn()
const mockGetDashboardRanking = vi.fn()
const mockGetDashboardWeeklyTrend = vi.fn()
const mockGetEmployeeProfile = vi.fn()
const mockGetActivityFeed = vi.fn()
const mockGetDashboardExceptions = vi.fn()
const mockGetRecentChecklists = vi.fn()
const mockListStores = vi.fn()
const mockListTaskAssignments = vi.fn()
const mockListEmployees = vi.fn()

vi.mock('../../services/dashboardService', () => ({
  getDashboardSummary: (...args: unknown[]) => mockGetDashboardSummary(...args),
  getDashboardRanking: (...args: unknown[]) => mockGetDashboardRanking(...args),
  getDashboardWeeklyTrend: (...args: unknown[]) => mockGetDashboardWeeklyTrend(...args),
  getEmployeeProfile: (...args: unknown[]) => mockGetEmployeeProfile(...args),
  getActivityFeed: (...args: unknown[]) => mockGetActivityFeed(...args),
  getDashboardExceptions: (...args: unknown[]) => mockGetDashboardExceptions(...args),
  getRecentChecklists: (...args: unknown[]) => mockGetRecentChecklists(...args),
}))

vi.mock('../../services/storeService', () => ({
  listStores: (...args: unknown[]) => mockListStores(...args),
}))

vi.mock('../../services/taskAssignmentService', () => ({
  listTaskAssignments: (...args: unknown[]) => mockListTaskAssignments(...args),
}))

vi.mock('../../services/employeeService', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
}))

const mockListSectors = vi.fn()

vi.mock('../../services/sectorService', () => ({
  listSectors: (...args: unknown[]) => mockListSectors(...args),
}))

let mockUser: User = {
  id: 1,
  name: 'Gestora',
  email: 'gestora@kijapa.com',
  role: 'GESTOR',
  store_id: 1,
  active: true,
  must_change_password: false,
}

vi.mock('../../auth/useAuth', () => ({
  useAuth: () => ({ user: mockUser, isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}))

const summary: DashboardSummary = {
  total_tasks: 20,
  completed_tasks: 15,
  pending_tasks: 5,
  completion_rate: 75,
  checklist_divergent_count: 2,
}

const ranking: EmployeeRankingEntry[] = [
  {
    employee_id: 1,
    employee_name: 'Ana Souza',
    completed_count: 8,
    avg_execution_seconds: 4320,
    on_time_count: 6,
    late_count: 2,
    on_time_rate: 75,
  },
  {
    employee_id: 2,
    employee_name: 'Bruno Lima',
    completed_count: 5,
    avg_execution_seconds: null,
    on_time_count: 5,
    late_count: 0,
    on_time_rate: 100,
  },
]

const trend: WeeklyTrendPoint[] = [
  { day_of_week: 'MONDAY', completed_count: 5, avg_execution_seconds: 600 },
  { day_of_week: 'TUESDAY', completed_count: 4, avg_execution_seconds: 900 },
]

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin']}>
        <SelectedStoreProvider>
          <AdminDashboardPage />
        </SelectedStoreProvider>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AdminDashboardPage', () => {
  beforeEach(() => {
    mockGetDashboardSummary.mockReset().mockResolvedValue(summary)
    mockGetDashboardRanking.mockReset().mockResolvedValue(ranking)
    mockGetDashboardWeeklyTrend.mockReset().mockResolvedValue(trend)
    mockGetEmployeeProfile.mockReset()
    mockGetActivityFeed.mockReset().mockResolvedValue([])
    mockGetDashboardExceptions.mockReset().mockResolvedValue([])
    mockGetRecentChecklists.mockReset().mockResolvedValue([])
    mockListStores.mockReset().mockResolvedValue([])
    mockListTaskAssignments.mockReset().mockResolvedValue([])
    mockListEmployees.mockReset().mockResolvedValue([])
    mockListSectors.mockReset().mockResolvedValue([])
    mockUser = {
      id: 1,
      name: 'Gestora',
      email: 'gestora@kijapa.com',
      role: 'GESTOR',
      store_id: 1,
      active: true,
      must_change_password: false,
    }
  })

  it('renderiza os cards de KPI com os valores vindos do resumo', async () => {
    renderPage()

    expect(await screen.findByText('75%')).toBeInTheDocument()
    expect(screen.getByText('Taxa de Conclusão')).toBeInTheDocument()

    expect(screen.getByText('Tarefas Concluídas')).toBeInTheDocument()
    expect(screen.getByText('15')).toBeInTheDocument()

    expect(screen.getByText('Tarefas Pendentes (agora)')).toBeInTheDocument()
    expect(screen.getByText('5')).toBeInTheDocument()

    expect(screen.getByText('Checklists Divergentes')).toBeInTheDocument()
    expect(screen.getByText('2')).toBeInTheDocument()
  })

  it('renderiza o ranking com nomes, percentuais e duração média formatada', async () => {
    renderPage()

    expect(await screen.findByText('Ana Souza')).toBeInTheDocument()
    expect(screen.getByText(/8 concluída\(s\)/)).toBeInTheDocument()
    expect(screen.getByText(/1h 12min em média/)).toBeInTheDocument()
    expect(screen.getByText('75% no prazo')).toBeInTheDocument()

    expect(screen.getByText('Bruno Lima')).toBeInTheDocument()
    expect(screen.getByText(/5 concluída\(s\)/)).toBeInTheDocument()
    expect(screen.getByText('100% no prazo')).toBeInTheDocument()
  })

  it('mostra o total de concluídas no lugar do percentual quando ninguém tinha SLA configurado', async () => {
    mockGetDashboardRanking.mockResolvedValueOnce([
      {
        employee_id: 3,
        employee_name: 'Carla Dias',
        completed_count: 12,
        avg_execution_seconds: null,
        on_time_count: 0,
        late_count: 0,
        on_time_rate: null,
      },
    ])
    renderPage()

    const button = await screen.findByRole('button', { name: /Carla Dias/ })
    expect(within(button).getByText('12')).toBeInTheDocument()
  })

  it('clicar em um funcionário do ranking abre o Raio-X com os dados do perfil', async () => {
    const profile: EmployeeProfile = {
      employee_id: 1,
      employee_name: 'Ana Souza',
      completed_count: 8,
      avg_execution_seconds: 4320,
      on_time_count: 6,
      late_count: 2,
      on_time_rate: 75,
      tasks: [],
    }
    mockGetEmployeeProfile.mockResolvedValue(profile)
    const user = userEvent.setup()
    renderPage()

    const anaButton = await screen.findByRole('button', { name: /Ana Souza/ })
    await user.click(anaButton)

    expect(await screen.findByText('Raio-X — Ana Souza')).toBeInTheDocument()
    expect(mockGetEmployeeProfile).toHaveBeenCalledWith(1, expect.objectContaining({}))
  })

  it('escolher um setor refaz o ranking filtrado', async () => {
    mockListSectors.mockResolvedValue([
      { id: 9, store_id: 1, name: 'Sushi', active: true },
      { id: 10, store_id: 1, name: 'Atendimento', active: true },
    ])
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ana Souza')
    mockGetDashboardRanking.mockClear()

    const sectorSelect = await screen.findByRole('combobox', { name: 'Setor (ranking)' })
    await user.selectOptions(sectorSelect, '9')

    await waitFor(() => {
      expect(mockGetDashboardRanking).toHaveBeenCalledWith(expect.objectContaining({ sectorId: 9 }))
    })
  })

  it('"Ver todos" em Alertas e Exceções abre a listagem completa com filtro de período', async () => {
    mockGetDashboardExceptions.mockResolvedValue([])
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ana Souza')
    const exceptionsHeader = screen.getByText('Alertas e Exceções').closest('div')!
    await user.click(within(exceptionsHeader).getByRole('button', { name: 'Ver todos' }))

    expect(await screen.findByText('Alertas e Exceções — todos')).toBeInTheDocument()
    // O modal reaproveita o mesmo filtro de período de Hoje/7 dias/Mês/Personalizado
    // do resto do painel — por isso aparece duas vezes em tela agora.
    expect(screen.getAllByRole('button', { name: 'Personalizado' })).toHaveLength(2)
    expect(mockGetDashboardExceptions).toHaveBeenCalledWith(
      expect.objectContaining({ startDate: expect.any(String), endDate: expect.any(String), limit: 200 }),
    )
  })

  it('"Ver todos" abre a Lista de Funcionários com todos os ativos da loja', async () => {
    mockListEmployees.mockResolvedValue([
      { id: 1, store_id: 1, name: 'Ana Souza', role_title: null, active: true, has_pin: true },
      { id: 9, store_id: 1, name: 'Funcionário Sem Conclusões', role_title: 'Estoquista', active: true, has_pin: true },
    ])
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ana Souza')
    const rankingHeader = screen.getByText('Top 5 Funcionários').closest('div')!
    await user.click(within(rankingHeader).getByRole('button', { name: 'Ver todos' }))

    expect(await screen.findByText('Lista de Funcionários')).toBeInTheDocument()
    // O funcionário sem nenhuma conclusão não aparece no ranking, mas aparece
    // na lista completa — é exatamente o problema que este modal resolve.
    expect(screen.getByText('Funcionário Sem Conclusões')).toBeInTheDocument()
    expect(screen.getByText('Estoquista')).toBeInTheDocument()
  })

  it('clicar num funcionário da Lista de Funcionários fecha a lista e abre o Raio-X dele', async () => {
    mockListEmployees.mockResolvedValue([
      { id: 9, store_id: 1, name: 'Funcionário Sem Conclusões', role_title: null, active: true, has_pin: true },
    ])
    mockGetEmployeeProfile.mockResolvedValue({
      employee_id: 9,
      employee_name: 'Funcionário Sem Conclusões',
      completed_count: 0,
      avg_execution_seconds: null,
      on_time_count: 0,
      late_count: 0,
      on_time_rate: null,
      tasks: [],
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Ana Souza')
    const rankingHeader = screen.getByText('Top 5 Funcionários').closest('div')!
    await user.click(within(rankingHeader).getByRole('button', { name: 'Ver todos' }))
    await user.click(await screen.findByText('Funcionário Sem Conclusões'))

    expect(screen.queryByText('Lista de Funcionários')).not.toBeInTheDocument()
    expect(await screen.findByText('Raio-X — Funcionário Sem Conclusões')).toBeInTheDocument()
  })

  it('mostra as entradas do Radar Ao Vivo com hora, autor e descrição', async () => {
    mockGetActivityFeed.mockResolvedValue([
      { id: 'a1', actor_name: 'Carla Dias', description: 'concluiu Lavar louça', occurred_at: '2026-09-13T14:05:00Z' },
    ])
    renderPage()

    expect(await screen.findByText('11:05')).toBeInTheDocument()
    expect(screen.getByText('Carla Dias')).toBeInTheDocument()
    expect(screen.getByText(/concluiu Lavar louça/)).toBeInTheDocument()
  })

  it('GESTOR não vê o seletor de loja', async () => {
    renderPage()

    await screen.findByText('Taxa de Conclusão')
    expect(screen.queryByRole('combobox', { name: 'Loja' })).not.toBeInTheDocument()
    expect(screen.queryByText('Todas as lojas')).not.toBeInTheDocument()
  })

  it('LIDER não vê o seletor de loja', async () => {
    mockUser = { ...mockUser, role: 'LIDER' }
    renderPage()

    await screen.findByText('Taxa de Conclusão')
    expect(screen.queryByRole('combobox', { name: 'Loja' })).not.toBeInTheDocument()
    expect(screen.queryByText('Todas as lojas')).not.toBeInTheDocument()
  })

  it('MASTER vê o seletor de loja e trocar de loja refaz as buscas com o novo storeId', async () => {
    mockUser = { ...mockUser, role: 'MASTER', store_id: null }
    mockListStores.mockResolvedValue([
      { id: 1, name: 'Loja A', brand: null, active: true },
      { id: 2, name: 'Loja B', brand: null, active: true },
    ])
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByText('Todas as lojas')).toBeInTheDocument()
    const select = screen.getByRole('combobox', { name: 'Loja' })

    await waitFor(() => expect(mockGetDashboardSummary).toHaveBeenCalled())
    mockGetDashboardSummary.mockClear()

    await user.selectOptions(select, '2')

    await waitFor(() => expect(mockGetDashboardSummary).toHaveBeenCalled())
    const params = mockGetDashboardSummary.mock.calls[mockGetDashboardSummary.mock.calls.length - 1][0]
    expect(params.storeId).toBe(2)
  })

  it('mostra mensagem de "nenhuma atividade" quando o ranking vem vazio', async () => {
    mockGetDashboardRanking.mockResolvedValue([])
    renderPage()

    expect(await screen.findByText('Nenhuma atividade registrada neste período.')).toBeInTheDocument()
  })

  it('"Operação em Andamento" mostra o funcionário e a tarefa de uma atribuição em andamento', async () => {
    const inProgressAssignment: TaskAssignment = {
      id: 100,
      task_id: 5,
      store_id: 1,
      day_of_week: 'MONDAY',
      task_title: 'Organizar salão',
      task_description: null,
      estimated_duration_minutes: null,
      requires_photo_proof: false,
      shift: 'Manhã',
      sector_id: 1,
      sector_name: 'Salão',
      status: 'IN_PROGRESS',
      started_at: '2026-09-13T12:00:00Z',
      completed_at: null,
      started_by_employee_id: 9,
      completed_by_employee_id: null,
      started_by_user_id: null,
      completed_by_user_id: null,
      result: null,
      justification: null,
      observation: null,
      photo_url: null,
      extra_photo_urls: [],
      elapsed_seconds: 120,
      active_participants: [{ employee_id: 9, employee_name: 'Diego Ferreira', started_at: '2026-09-13T12:00:00Z' }],
      blocked_at: null,
      block_reason: null,
      blocked_by_employee_id: null,
      latest_execution_history_id: null,
    }
    mockListTaskAssignments.mockResolvedValue([inProgressAssignment])

    renderPage()

    expect(await screen.findByText(/Diego Ferreira/)).toBeInTheDocument()
    expect(screen.getByText('Organizar salão')).toBeInTheDocument()
    expect(mockListTaskAssignments).toHaveBeenCalledWith(expect.objectContaining({ status: 'IN_PROGRESS' }))
  })

  it('"Alertas e Exceções" mostra tarefas com o badge "Tarefa"', async () => {
    const exceptions: ExceptionEntry[] = [
      {
        id: 'task:1',
        type: 'TAREFA',
        title: 'Limpar fritadeira',
        user_name: 'Ana Souza',
        date: '2026-09-13T14:00:00Z',
        reason: 'Fritadeira quebrada.',
      },
      {
        id: 'task:2',
        type: 'TAREFA',
        title: 'Organizar estoque',
        user_name: 'Bruno Lima',
        date: '2026-09-13T14:00:00Z',
        reason: 'Faltou 1 caixa de guardanapos.',
      },
    ]
    mockGetDashboardExceptions.mockResolvedValue(exceptions)
    renderPage()

    expect(await screen.findByText('Limpar fritadeira', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/Fritadeira quebrada/)).toBeInTheDocument()

    expect(screen.getByText('Organizar estoque', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/Faltou 1 caixa de guardanapos/)).toBeInTheDocument()

    expect(screen.getAllByText('Tarefa')).toHaveLength(2)
  })

  it('"Alertas e Exceções" mostra divergências de checklist com o badge "Checklist"', async () => {
    const exceptions: ExceptionEntry[] = [
      {
        id: 'checklist:1',
        type: 'CHECKLIST',
        title: 'Desligar a fritadeira',
        user_name: 'Carlos Executor',
        date: '2026-09-13T14:00:00Z',
        reason: 'Fritadeira ficou ligada.',
      },
    ]
    mockGetDashboardExceptions.mockResolvedValue(exceptions)
    renderPage()

    expect(await screen.findByText('Desligar a fritadeira', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Carlos Executor', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/Fritadeira ficou ligada/)).toBeInTheDocument()
    expect(screen.getByText('Checklist')).toBeInTheDocument()
  })

  it('"Alertas e Exceções" mostra tarefas impedidas com o badge "Impedimento"', async () => {
    const exceptions: ExceptionEntry[] = [
      {
        id: 'impedimento:1',
        type: 'IMPEDIMENTO',
        title: 'Descongelar camarão',
        user_name: 'Ana Souza',
        date: '2026-09-13T14:00:00Z',
        reason: 'Faltou camarão no estoque.',
      },
    ]
    mockGetDashboardExceptions.mockResolvedValue(exceptions)
    renderPage()

    expect(await screen.findByText('Descongelar camarão', { exact: false })).toBeInTheDocument()
    expect(screen.getByText(/Faltou camarão no estoque/)).toBeInTheDocument()
    expect(screen.getByText('Impedimento')).toBeInTheDocument()
  })

  it('mostra mensagem de sucesso quando não há exceções no período', async () => {
    renderPage()

    expect(await screen.findByText(/Nenhuma exceção registrada neste período/)).toBeInTheDocument()
  })

  it('"Últimos Checklists" mostra quem executou e quem validou', async () => {
    const recentChecklists: RecentChecklistEntry[] = [
      {
        id: 1,
        template_name: 'Fechamento da Cozinha',
        shift: 'NOITE',
        status: 'COMPLETED',
        fully_validated: true,
        executed_by_name: 'Carla Dias',
        validated_by_names: ['Diego Ferreira'],
        started_at: '2026-09-13T22:00:00Z',
        finished_at: '2026-09-13T22:30:00Z',
      },
    ]
    mockGetRecentChecklists.mockResolvedValue(recentChecklists)
    renderPage()

    expect(await screen.findByText('Fechamento da Cozinha', { exact: false })).toBeInTheDocument()
    expect(screen.getByText('Carla Dias')).toBeInTheDocument()
    expect(screen.getByText('Diego Ferreira')).toBeInTheDocument()
    expect(screen.getByText('Validado')).toBeInTheDocument()
  })
})
