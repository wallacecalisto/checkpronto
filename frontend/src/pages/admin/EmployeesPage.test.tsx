import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { Employee } from '../../types/employee'
import { EmployeesPage } from './EmployeesPage'

const mockListEmployees = vi.fn()
const mockCreateEmployee = vi.fn()
const mockUpdateEmployee = vi.fn()
const mockDeleteEmployee = vi.fn()
const mockListStores = vi.fn()
const mockListSectors = vi.fn()

vi.mock('../../services/employeeService', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
  createEmployee: (...args: unknown[]) => mockCreateEmployee(...args),
  updateEmployee: (...args: unknown[]) => mockUpdateEmployee(...args),
  deleteEmployee: (...args: unknown[]) => mockDeleteEmployee(...args),
}))

vi.mock('../../services/storeService', () => ({
  listStores: (...args: unknown[]) => mockListStores(...args),
}))

vi.mock('../../services/sectorService', () => ({
  listSectors: (...args: unknown[]) => mockListSectors(...args),
}))

const sector = { id: 1, store_id: 1, name: 'Cozinha', active: true }

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

const employee: Employee = {
  id: 1,
  store_id: 1,
  sector_id: 1,
  name: 'Carlos Ajudante',
  role_title: 'Cozinheiro',
  active: true,
  has_pin: true,
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <EmployeesPage />
    </QueryClientProvider>,
  )
}

describe('EmployeesPage', () => {
  beforeEach(() => {
    mockListEmployees.mockReset()
    mockCreateEmployee.mockReset()
    mockUpdateEmployee.mockReset()
    mockDeleteEmployee.mockReset()
    mockListStores.mockReset()
    mockListSectors.mockReset().mockResolvedValue([sector])
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

  it('lista os funcionários vindos da API', async () => {
    mockListEmployees.mockResolvedValueOnce([employee])
    renderPage()

    expect(await screen.findByText('Carlos Ajudante')).toBeInTheDocument()
    expect(screen.getByText('Cozinheiro')).toBeInTheDocument()
    expect(screen.getByText('Definido')).toBeInTheDocument()
    expect(await screen.findByText('Cozinha')).toBeInTheDocument()
  })

  it('cria um funcionário novo (GESTOR não vê seletor de loja)', async () => {
    mockListEmployees.mockResolvedValue([])
    mockCreateEmployee.mockResolvedValueOnce({ ...employee, id: 2, name: 'Novo Funcionário' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo funcionário/i }))
    expect(screen.queryByLabelText('Loja')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Nome'), 'Novo Funcionário')
    await user.selectOptions(await screen.findByLabelText('Setor'), 'Cozinha')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateEmployee).toHaveBeenCalledWith({
        name: 'Novo Funcionário',
        role_title: undefined,
        store_id: undefined,
        sector_id: sector.id,
      })
    })
  })

  it('MASTER vê o seletor de loja obrigatório ao criar', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListEmployees.mockResolvedValue([])
    mockListStores.mockResolvedValueOnce([{ id: 5, name: 'Loja Central', brand: null, active: true }])
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo funcionário/i }))
    expect(await screen.findByLabelText('Loja')).toBeRequired()
  })

  it('edita um funcionário existente', async () => {
    mockListEmployees.mockResolvedValue([employee])
    mockUpdateEmployee.mockResolvedValueOnce({ ...employee, name: 'Nome Editado' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))
    const nameInput = screen.getByLabelText('Nome')
    await user.clear(nameInput)
    await user.type(nameInput, 'Nome Editado')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateEmployee).toHaveBeenCalledWith(employee.id, {
        name: 'Nome Editado',
        role_title: 'Cozinheiro',
        sector_id: employee.sector_id,
      })
    })
  })

  it('mostra o erro vindo da API quando a criação falha', async () => {
    mockListEmployees.mockResolvedValue([])
    mockCreateEmployee.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Já existe um funcionário com esse nome.', code: 'CONFLICT' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo funcionário/i }))
    await user.type(screen.getByLabelText('Nome'), 'Repetido')
    await user.selectOptions(await screen.findByLabelText('Setor'), 'Cozinha')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/já existe um funcionário/i)
  })

  it('ativa/desativa um funcionário direto na tabela', async () => {
    mockListEmployees.mockResolvedValue([employee])
    mockUpdateEmployee.mockResolvedValueOnce({ ...employee, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Desativar' }))

    await waitFor(() => {
      expect(mockUpdateEmployee).toHaveBeenCalledWith(employee.id, { active: false })
    })
  })

  // "Modo Deus" --------------------------------------------------

  it('não mostra o botão "Excluir" para GESTOR', async () => {
    mockListEmployees.mockResolvedValue([employee])
    renderPage()

    await screen.findByText('Carlos Ajudante')
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
    mockListEmployees.mockResolvedValue([employee])
    mockDeleteEmployee.mockResolvedValueOnce({ ...employee, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    expect(await screen.findByText('Excluir funcionário')).toBeInTheDocument()
    expect(mockDeleteEmployee).not.toHaveBeenCalled()

    // Duas "Excluir" na tela agora: o botão da linha e o de confirmar no modal.
    const confirmButton = screen.getAllByRole('button', { name: 'Excluir' })[1]
    await user.click(confirmButton)

    await waitFor(() => expect(mockDeleteEmployee).toHaveBeenCalledWith(employee.id))
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
    mockListEmployees.mockResolvedValue([employee])
    mockDeleteEmployee.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Funcionário não encontrado.', code: 'NOT_FOUND' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    await user.click(screen.getAllByRole('button', { name: 'Excluir' })[1])

    expect(await screen.findByRole('alert')).toHaveTextContent(/não encontrado/i)
  })
})
