import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { AuditLog } from '../../types/auditLog'
import { AuditPage } from './AuditPage'

const mockListAuditLogs = vi.fn()
const mockListStores = vi.fn()

vi.mock('../../services/auditService', () => ({
  listAuditLogs: (...args: unknown[]) => mockListAuditLogs(...args),
}))

vi.mock('../../services/storeService', () => ({
  listStores: (...args: unknown[]) => mockListStores(...args),
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

const entry: AuditLog = {
  id: 1,
  store_id: 1,
  store_name: 'Cozinha Pinheiros',
  actor_type: 'USER',
  actor_user_id: 7,
  actor_employee_id: null,
  actor_name: 'Gestora Ana',
  action: 'UPDATE',
  entity_type: 'EMPLOYEE',
  entity_id: 42,
  before_data: { name: 'Nome Antigo', active: true },
  after_data: { name: 'Nome Novo', active: true },
  created_at: '2026-09-10T14:30:00Z',
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/audit']}>
        <AuditPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('AuditPage', () => {
  beforeEach(() => {
    mockListAuditLogs.mockReset()
    mockListStores.mockReset()
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

  it('lista os registros vindos da API, com o preset "Últimos 7 dias" marcado', async () => {
    mockListAuditLogs.mockResolvedValue([entry])
    renderPage()

    expect(await screen.findByRole('cell', { name: /Gestora Ana/ })).toBeInTheDocument()
    expect(await screen.findByText(/Funcionário \(Nome Novo\)/)).toBeInTheDocument()

    const sevenDaysButton = await screen.findByRole('button', { name: 'Últimos 7 dias' })
    expect(sevenDaysButton.className).toMatch(/bg-emerald-500/)
  })

  it('cai de volta para "#id" quando a entidade não tem um campo de nome óbvio', async () => {
    const assignmentEntry: AuditLog = {
      ...entry,
      id: 2,
      entity_type: 'TASK_ASSIGNMENT',
      before_data: { status: 'PENDING' },
      after_data: { status: 'IN_PROGRESS' },
    }
    mockListAuditLogs.mockResolvedValue([assignmentEntry])
    renderPage()

    expect(await screen.findByText(/Agendamento #42/)).toBeInTheDocument()
  })

  it('GESTOR não vê a coluna Loja nem o seletor de loja (não pode listar todas)', async () => {
    mockListAuditLogs.mockResolvedValue([entry])
    renderPage()

    await screen.findByText('Edição')
    expect(screen.queryByText('Cozinha Pinheiros')).not.toBeInTheDocument()
    expect(screen.queryByText('Todas as lojas')).not.toBeInTheDocument()
  })

  it('MASTER vê a coluna Loja e o seletor de loja', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListAuditLogs.mockResolvedValue([entry])
    mockListStores.mockResolvedValue([{ id: 1, name: 'Cozinha Pinheiros', brand: null, active: true }])
    renderPage()

    expect(await screen.findByRole('cell', { name: 'Cozinha Pinheiros' })).toBeInTheDocument()
    expect(await screen.findByText('Todas as lojas')).toBeInTheDocument()
  })

  it('o filtro de ator é populado a partir dos registros carregados', async () => {
    mockListAuditLogs.mockResolvedValue([entry])
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Edição')
    await user.click(screen.getByPlaceholderText(/buscar funcionário/i))
    expect(await screen.findByRole('button', { name: 'Gestora Ana' })).toBeInTheDocument()
  })

  it('"Ver detalhes" abre o modal com a comparação antes/depois', async () => {
    mockListAuditLogs.mockResolvedValue([entry])
    const user = userEvent.setup()
    renderPage()

    const detailsButton = await screen.findByRole('button', { name: 'Ver detalhes' })
    await user.click(detailsButton)

    expect(screen.getByText('Detalhes da ação')).toBeInTheDocument()
    expect(screen.getByText('Nome Antigo')).toBeInTheDocument()
    expect(screen.getByText('Nome Novo')).toBeInTheDocument()
  })

  it('trocar para "Hoje" refaz a busca com o dia de hoje', async () => {
    mockListAuditLogs.mockResolvedValue([entry])
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(mockListAuditLogs).toHaveBeenCalled())
    mockListAuditLogs.mockClear()

    await user.click(screen.getByRole('button', { name: 'Hoje' }))

    await waitFor(() => expect(mockListAuditLogs).toHaveBeenCalled())
    const params = mockListAuditLogs.mock.calls[0][0]
    expect(params.dateFrom).toBe(params.dateTo)
  })
})
