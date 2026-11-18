import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { Task } from '../../types/task'
import { TasksPage } from './TasksPage'

const mockListTasks = vi.fn()
const mockCreateTask = vi.fn()
const mockUpdateTask = vi.fn()
const mockDeleteTask = vi.fn()
const mockListStores = vi.fn()

vi.mock('../../services/taskService', () => ({
  listTasks: (...args: unknown[]) => mockListTasks(...args),
  createTask: (...args: unknown[]) => mockCreateTask(...args),
  updateTask: (...args: unknown[]) => mockUpdateTask(...args),
  deleteTask: (...args: unknown[]) => mockDeleteTask(...args),
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
  useAuth: () => ({
    user: mockUser,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    setUser: vi.fn(),
  }),
}))

const task: Task = {
  id: 1,
  store_id: 1,
  title: 'Lavar louça',
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
      <TasksPage />
    </QueryClientProvider>,
  )
}

describe('TasksPage', () => {
  beforeEach(() => {
    mockListTasks.mockReset()
    mockCreateTask.mockReset()
    mockUpdateTask.mockReset()
    mockDeleteTask.mockReset()
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

  it('lista as tarefas do catálogo vindas da API', async () => {
    mockListTasks.mockResolvedValueOnce([task])
    renderPage()

    expect(await screen.findByText('Lavar louça')).toBeInTheDocument()
    expect(screen.getByText('Ativa')).toBeInTheDocument()
  })

  it('mostra a coluna SLA com os minutos configurados, ou "—" quando não há', async () => {
    mockListTasks.mockResolvedValueOnce([task, { ...task, id: 2, title: 'Fazer 150 filadélfias', estimated_duration_minutes: 30 }])
    renderPage()

    expect(await screen.findByText('Fazer 150 filadélfias')).toBeInTheDocument()
    expect(screen.getByText('30 min')).toBeInTheDocument()
    expect(screen.getByText('—')).toBeInTheDocument()
  })

  it('filtra a lista pelo nome, em tempo real e client-side', async () => {
    mockListTasks.mockResolvedValueOnce([
      { ...task, id: 1, title: 'Lavar louça' },
      { ...task, id: 2, title: 'Fazer 150 filadélfias' },
    ])
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByText('Lavar louça')).toBeInTheDocument()
    expect(screen.getByText('Fazer 150 filadélfias')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Buscar tarefa'), 'filad')

    expect(screen.queryByText('Lavar louça')).not.toBeInTheDocument()
    expect(screen.getByText('Fazer 150 filadélfias')).toBeInTheDocument()
    // Chamada nenhuma nova ao backend — o filtro é inteiramente local.
    expect(mockListTasks).toHaveBeenCalledTimes(1)
  })

  it('esconde tarefas inativas até marcar "Mostrar inativas"', async () => {
    mockListTasks.mockResolvedValueOnce([{ ...task, id: 2, title: 'Desligada', active: false }])
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(mockListTasks).toHaveBeenCalled())
    expect(screen.queryByText('Desligada')).not.toBeInTheDocument()

    await user.click(screen.getByLabelText(/mostrar inativas/i))
    expect(await screen.findByText('Desligada')).toBeInTheDocument()
  })

  it('cria uma tarefa nova (GESTOR, sem seletor de loja)', async () => {
    mockListTasks.mockResolvedValue([])
    mockCreateTask.mockResolvedValueOnce({ ...task, id: 2, title: 'Nova Tarefa' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /nova tarefa/i }))
    expect(screen.queryByLabelText('Loja')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Título'), 'Nova Tarefa')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledWith({
        title: 'Nova Tarefa',
        description: undefined,
        estimated_duration_minutes: undefined,
        requires_photo_proof: false,
        store_id: undefined,
      })
    })
  })

  it('preenche o Tempo Estimado ao criar e envia como número', async () => {
    mockListTasks.mockResolvedValue([])
    mockCreateTask.mockResolvedValueOnce({ ...task, id: 3, title: 'Tarefa com SLA', estimated_duration_minutes: 45 })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /nova tarefa/i }))
    await user.type(screen.getByLabelText('Título'), 'Tarefa com SLA')
    await user.type(screen.getByLabelText(/tempo estimado/i), '45')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateTask).toHaveBeenCalledWith({
        title: 'Tarefa com SLA',
        description: undefined,
        estimated_duration_minutes: 45,
        requires_photo_proof: false,
        store_id: undefined,
      })
    })
  })

  it('MASTER precisa escolher uma loja para criar uma tarefa', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListTasks.mockResolvedValue([])
    mockListStores.mockResolvedValue([{ id: 5, name: 'Loja Central', brand: null, active: true }])
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /nova tarefa/i }))
    expect(await screen.findByLabelText('Loja')).toBeRequired()
  })

  it('edita título/descrição de uma tarefa existente', async () => {
    mockListTasks.mockResolvedValue([task])
    mockUpdateTask.mockResolvedValueOnce({ ...task, title: 'Título Editado' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))

    const titleInput = screen.getByLabelText('Título')
    await user.clear(titleInput)
    await user.type(titleInput, 'Título Editado')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateTask).toHaveBeenCalledWith(task.id, {
        title: 'Título Editado',
        description: undefined,
        estimated_duration_minutes: null,
        requires_photo_proof: false,
      })
    })
  })

  it('ativa/desativa uma tarefa direto na tabela', async () => {
    mockListTasks.mockResolvedValue([task])
    mockUpdateTask.mockResolvedValueOnce({ ...task, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Desativar' }))

    await waitFor(() => {
      expect(mockUpdateTask).toHaveBeenCalledWith(task.id, { active: false })
    })
  })

  it('mostra o erro vindo da API quando a criação falha', async () => {
    mockListTasks.mockResolvedValue([])
    mockCreateTask.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Já existe uma tarefa com esse título.', code: 'CONFLICT' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /nova tarefa/i }))
    await user.type(screen.getByLabelText('Título'), 'Tarefa X')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/já existe uma tarefa/i)
  })

  // "Modo Deus" --------------------------------------------------

  it('não mostra o botão "Excluir" para GESTOR', async () => {
    mockListTasks.mockResolvedValue([task])
    renderPage()

    await screen.findByText('Lavar louça')
    expect(screen.queryByRole('button', { name: 'Excluir' })).not.toBeInTheDocument()
  })

  it('MASTER vê o botão "Excluir" e confirma num modal antes de excluir', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListTasks.mockResolvedValue([task])
    mockDeleteTask.mockResolvedValueOnce({ ...task, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    expect(await screen.findByText('Excluir tarefa')).toBeInTheDocument()
    expect(mockDeleteTask).not.toHaveBeenCalled()

    const confirmButton = screen.getAllByRole('button', { name: 'Excluir' })[1]
    await user.click(confirmButton)

    await waitFor(() => expect(mockDeleteTask).toHaveBeenCalledWith(task.id))
  })

  it('mostra o erro da API se a exclusão falhar', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListTasks.mockResolvedValue([task])
    mockDeleteTask.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Tarefa não encontrada.', code: 'NOT_FOUND' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    await user.click(screen.getAllByRole('button', { name: 'Excluir' })[1])

    expect(await screen.findByRole('alert')).toHaveTextContent(/não encontrada/i)
  })
})
