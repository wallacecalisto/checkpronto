import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { Sector } from '../../types/sector'
import type { Task } from '../../types/task'
import { currentDayOfWeek, type TaskAssignment } from '../../types/taskAssignment'
import { TaskAssignmentsPage } from './TaskAssignmentsPage'

const mockListTaskAssignments = vi.fn()
const mockCreateTaskAssignment = vi.fn()
const mockUpdateTaskAssignment = vi.fn()
const mockDeleteTaskAssignment = vi.fn()

vi.mock('../../services/taskAssignmentService', () => ({
  listTaskAssignments: (...args: unknown[]) => mockListTaskAssignments(...args),
  createTaskAssignment: (...args: unknown[]) => mockCreateTaskAssignment(...args),
  updateTaskAssignment: (...args: unknown[]) => mockUpdateTaskAssignment(...args),
  deleteTaskAssignment: (...args: unknown[]) => mockDeleteTaskAssignment(...args),
}))

const mockListTasks = vi.fn()
vi.mock('../../services/taskService', () => ({
  listTasks: (...args: unknown[]) => mockListTasks(...args),
}))

const mockListSectors = vi.fn()
vi.mock('../../services/sectorService', () => ({
  listSectors: (...args: unknown[]) => mockListSectors(...args),
}))

const mockListStores = vi.fn()
vi.mock('../../services/storeService', () => ({
  listStores: (...args: unknown[]) => mockListStores(...args),
}))

const mockGetStoreSettings = vi.fn()
vi.mock('../../services/storeSettingsService', () => ({
  getStoreSettings: (...args: unknown[]) => mockGetStoreSettings(...args),
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

const cozinha: Sector = { id: 1, store_id: 1, name: 'Cozinha', active: true }
const today = currentDayOfWeek()

const assignment: TaskAssignment = {
  id: 1,
  task_id: 1,
  store_id: 1,
  day_of_week: today,
  task_title: 'Abrir a loja',
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

const task: Task = {
  id: 1,
  store_id: 1,
  title: 'Abrir a loja',
  description: null,
  estimated_duration_minutes: null,
  requires_photo_proof: false,
  active: true,
  created_by_user_id: 1,
  created_at: '2026-01-01T00:00:00Z',
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <TaskAssignmentsPage />
    </QueryClientProvider>,
  )
}

describe('TaskAssignmentsPage', () => {
  beforeEach(() => {
    mockListTaskAssignments.mockReset().mockResolvedValue([assignment])
    mockCreateTaskAssignment.mockReset()
    mockUpdateTaskAssignment.mockReset()
    mockDeleteTaskAssignment.mockReset()
    mockListTasks.mockReset().mockResolvedValue([task])
    mockListSectors.mockReset().mockResolvedValue([cozinha])
    mockListStores.mockReset()
    mockGetStoreSettings.mockReset().mockResolvedValue({
      store_id: 1,
      max_assignees_per_task: null,
      operational_checklists_enabled: true,
      auto_logout_minutes: 5,
      hide_task_timer: false,
      require_live_photo_only: false,
      require_pin_on_complete: false,
      enable_audio_alerts: false,
      shifts: ['Manhã', 'Tarde', 'Noite'],
    })
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

  it('lista os agendamentos com a coluna Turno preenchida', async () => {
    renderPage()

    const taskCell = await screen.findByText('Abrir a loja')
    const row = taskCell.closest('tr') as HTMLElement
    expect(within(row).getByText('Cozinha')).toBeInTheDocument()
    expect(within(row).getByText('Manhã')).toBeInTheDocument()
  })

  it('filtro de turno vem de store_settings.shifts e refiltra a lista', async () => {
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Abrir a loja')
    mockListTaskAssignments.mockClear()

    const shiftSelect = await screen.findByLabelText('Filtrar por turno')
    await user.selectOptions(shiftSelect, 'Tarde')

    await waitFor(() => {
      expect(mockListTaskAssignments).toHaveBeenCalledWith(expect.objectContaining({ shift: 'Tarde' }))
    })
  })

  it('editar um agendamento mostra o turno atual, editável', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))

    const modalTitle = await screen.findByRole('heading', { name: 'Editar agendamento' })
    const modal = modalTitle.closest('.rounded-2xl') as HTMLElement
    expect(within(modal).getByText('Turno')).toBeInTheDocument()
    const shiftSelect = (await within(modal).findByLabelText('Turno')) as HTMLSelectElement
    expect(shiftSelect.value).toBe('Manhã')
  })
})
