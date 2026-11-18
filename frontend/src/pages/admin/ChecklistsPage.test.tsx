import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { ChecklistExecution } from '../../types/checklistExecution'
import { toISODateString } from '../../utils/dateTime'
import { ChecklistsPage } from './ChecklistsPage'

const mockListChecklistExecutions = vi.fn()
const mockListChecklistTemplates = vi.fn()

vi.mock('../../services/checklistService', () => ({
  listChecklistExecutions: (...args: unknown[]) => mockListChecklistExecutions(...args),
}))

vi.mock('../../services/checklistTemplateService', () => ({
  listChecklistTemplates: (...args: unknown[]) => mockListChecklistTemplates(...args),
}))

const mockUser: User = {
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

const execution: ChecklistExecution = {
  id: 1,
  template_id: 1,
  template_name: 'Fechamento da cozinha',
  store_id: 1,
  shift: 'MANHA',
  executed_by_user_id: 1,
  executed_by_employee_id: null,
  executed_by_name: 'Gestora',
  validated_by_names: [],
  started_at: '2026-09-10T08:00:00Z',
  finished_at: null,
  status: 'IN_PROGRESS',
  fully_validated: false,
  items: [],
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/checklists']}>
        <ChecklistsPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ChecklistsPage', () => {
  beforeEach(() => {
    mockListChecklistExecutions.mockReset()
    mockListChecklistTemplates.mockReset()
    mockListChecklistTemplates.mockResolvedValue([])
  })

  it('abre com o preset "Últimos 7 dias" marcado e busca com esse intervalo', async () => {
    mockListChecklistExecutions.mockResolvedValue([execution])
    renderPage()

    const sevenDaysButton = await screen.findByRole('button', { name: 'Últimos 7 dias' })
    expect(sevenDaysButton.className).toMatch(/bg-emerald-500/)

    await waitFor(() => expect(mockListChecklistExecutions).toHaveBeenCalled())
    const params = mockListChecklistExecutions.mock.calls[0][0]
    const today = toISODateString(new Date())
    expect(params.startedTo).toBe(today)
    expect(params.startedFrom).not.toBe(today)
  })

  it('mostra a coluna Data formatada antes da coluna Turno', async () => {
    mockListChecklistExecutions.mockResolvedValue([execution])
    renderPage()

    const headers = await screen.findAllByRole('columnheader')
    const headerTexts = headers.map((header) => header.textContent)
    expect(headerTexts.indexOf('Data')).toBeGreaterThan(-1)
    expect(headerTexts.indexOf('Data')).toBeLessThan(headerTexts.indexOf('Turno'))

    expect(await screen.findByText('10/09/2026')).toBeInTheDocument()
  })

  it('mostra as colunas "Executado por" e "Validado por"', async () => {
    mockListChecklistExecutions.mockResolvedValue([
      { ...execution, executed_by_name: 'Ana Souza', validated_by_names: ['Bruno Lima'] },
    ])
    renderPage()

    const headers = await screen.findAllByRole('columnheader')
    const headerTexts = headers.map((header) => header.textContent)
    expect(headerTexts).toContain('Executado por')
    expect(headerTexts).toContain('Validado por')

    expect(await screen.findByText('Ana Souza')).toBeInTheDocument()
    expect(screen.getByText('Bruno Lima')).toBeInTheDocument()
  })

  it('mostra "—" em "Validado por" quando ninguém validou ainda', async () => {
    mockListChecklistExecutions.mockResolvedValue([execution])
    renderPage()

    await screen.findByText('Fechamento da cozinha')
    const row = screen.getByText('Fechamento da cozinha').closest('tr')
    expect(row).not.toBeNull()
    expect(row?.textContent).toContain('—')
  })

  it('trocar para "Hoje" refaz a busca só com o dia de hoje', async () => {
    mockListChecklistExecutions.mockResolvedValue([execution])
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(mockListChecklistExecutions).toHaveBeenCalled())
    mockListChecklistExecutions.mockClear()

    await user.click(screen.getByRole('button', { name: 'Hoje' }))

    await waitFor(() => expect(mockListChecklistExecutions).toHaveBeenCalled())
    const params = mockListChecklistExecutions.mock.calls[0][0]
    const today = toISODateString(new Date())
    expect(params.startedFrom).toBe(today)
    expect(params.startedTo).toBe(today)
  })

  it('"Personalizado" revela os campos de data e permite escolher o intervalo livremente', async () => {
    mockListChecklistExecutions.mockResolvedValue([execution])
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(mockListChecklistExecutions).toHaveBeenCalled())
    expect(screen.queryByLabelText('De')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Personalizado' }))
    expect(screen.getByLabelText('De')).toBeInTheDocument()
    expect(screen.getByLabelText('Até')).toBeInTheDocument()

    mockListChecklistExecutions.mockClear()
    const fromInput = screen.getByLabelText('De')
    await user.clear(fromInput)
    await user.type(fromInput, '2026-01-01')

    await waitFor(() => {
      const params = mockListChecklistExecutions.mock.calls.at(-1)?.[0]
      expect(params.startedFrom).toBe('2026-01-01')
    })
  })
})
