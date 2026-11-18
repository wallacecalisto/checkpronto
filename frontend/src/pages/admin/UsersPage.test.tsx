import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import { UsersPage } from './UsersPage'

const mockListUsers = vi.fn()
const mockCreateUser = vi.fn()
const mockUpdateUser = vi.fn()
const mockDeleteUser = vi.fn()
const mockListStores = vi.fn()

vi.mock('../../services/userService', () => ({
  listUsers: (...args: unknown[]) => mockListUsers(...args),
  createUser: (...args: unknown[]) => mockCreateUser(...args),
  updateUser: (...args: unknown[]) => mockUpdateUser(...args),
  deleteUser: (...args: unknown[]) => mockDeleteUser(...args),
}))

vi.mock('../../services/storeService', () => ({
  listStores: (...args: unknown[]) => mockListStores(...args),
}))

const loggedInMaster: User = {
  id: 1,
  name: 'Master Logado',
  email: 'master@kijapa.com',
  role: 'MASTER',
  store_id: null,
  active: true,
  must_change_password: false,
}

vi.mock('../../auth/useAuth', () => ({
  useAuth: () => ({ user: loggedInMaster, isAuthenticated: true, isLoading: false, login: vi.fn(), logout: vi.fn() }),
}))

const otherUser: User = {
  id: 2,
  name: 'Gestora Loja A',
  email: 'gestora@kijapa.com',
  role: 'GESTOR',
  store_id: 5,
  active: true,
  must_change_password: false,
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <UsersPage />
    </QueryClientProvider>,
  )
}

// "Modo Deus": esta tela inteira já é exclusiva do MASTER (rota
// gateada em routes/AppRoutes.tsx) — o que muda aqui é só a exclusão em si.
describe('UsersPage', () => {
  beforeEach(() => {
    mockListUsers.mockReset()
    mockCreateUser.mockReset()
    mockUpdateUser.mockReset()
    mockDeleteUser.mockReset()
    mockListStores.mockReset().mockResolvedValue([])
  })

  it('lista os usuários vindos da API', async () => {
    mockListUsers.mockResolvedValue([otherUser])
    renderPage()

    expect(await screen.findByText('Gestora Loja A')).toBeInTheDocument()
    expect(screen.getByText('gestora@kijapa.com')).toBeInTheDocument()
  })

  it('não mostra "Excluir" na própria linha do MASTER logado', async () => {
    mockListUsers.mockResolvedValue([loggedInMaster, otherUser])
    renderPage()

    await screen.findByText('Gestora Loja A')
    // Só uma linha (a da Gestora) deve ter o botão "Excluir".
    expect(screen.getAllByRole('button', { name: 'Excluir' })).toHaveLength(1)
  })

  it('confirma num modal antes de excluir um usuário', async () => {
    mockListUsers.mockResolvedValue([otherUser])
    mockDeleteUser.mockResolvedValueOnce({ ...otherUser, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    expect(await screen.findByText('Excluir usuário')).toBeInTheDocument()
    expect(mockDeleteUser).not.toHaveBeenCalled()

    const confirmButton = screen.getAllByRole('button', { name: 'Excluir' })[1]
    await user.click(confirmButton)

    await waitFor(() => expect(mockDeleteUser).toHaveBeenCalledWith(otherUser.id))
  })

  it('mostra o erro da API se a exclusão falhar (ex.: tentativa de auto-exclusão)', async () => {
    mockListUsers.mockResolvedValue([otherUser])
    mockDeleteUser.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Você não pode excluir seu próprio usuário.', code: 'CANNOT_DELETE_SELF' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    await user.click(screen.getAllByRole('button', { name: 'Excluir' })[1])

    expect(await screen.findByRole('alert')).toHaveTextContent(/não pode excluir seu próprio usuário/i)
  })
})
