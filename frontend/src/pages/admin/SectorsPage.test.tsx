import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { Sector } from '../../types/sector'
import { SectorsPage } from './SectorsPage'

const mockListSectors = vi.fn()
const mockCreateSector = vi.fn()
const mockUpdateSector = vi.fn()
const mockDeleteSector = vi.fn()
const mockListStores = vi.fn()

vi.mock('../../services/sectorService', () => ({
  listSectors: (...args: unknown[]) => mockListSectors(...args),
  createSector: (...args: unknown[]) => mockCreateSector(...args),
  updateSector: (...args: unknown[]) => mockUpdateSector(...args),
  deleteSector: (...args: unknown[]) => mockDeleteSector(...args),
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

const sector: Sector = {
  id: 1,
  store_id: 1,
  name: 'Cozinha Quente',
  active: true,
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <SectorsPage />
    </QueryClientProvider>,
  )
}

describe('SectorsPage', () => {
  beforeEach(() => {
    mockListSectors.mockReset()
    mockCreateSector.mockReset()
    mockUpdateSector.mockReset()
    mockDeleteSector.mockReset()
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

  it('lista os setores vindos da API', async () => {
    mockListSectors.mockResolvedValueOnce([sector])
    renderPage()

    expect(await screen.findByText('Cozinha Quente')).toBeInTheDocument()
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })

  it('esconde setores inativos até marcar "Mostrar inativos"', async () => {
    mockListSectors.mockResolvedValueOnce([{ ...sector, id: 2, name: 'Setor Desligado', active: false }])
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(mockListSectors).toHaveBeenCalled())
    expect(screen.queryByText('Setor Desligado')).not.toBeInTheDocument()

    await user.click(screen.getByLabelText(/mostrar inativos/i))
    expect(await screen.findByText('Setor Desligado')).toBeInTheDocument()
  })

  it('cria um setor novo (GESTOR, sem seletor de loja)', async () => {
    mockListSectors.mockResolvedValue([])
    mockCreateSector.mockResolvedValueOnce({ ...sector, id: 2, name: 'Sushi' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo setor/i }))
    expect(screen.queryByLabelText('Loja')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Nome'), 'Sushi')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateSector).toHaveBeenCalledWith({ name: 'Sushi', store_id: undefined })
    })
  })

  it('MASTER precisa escolher uma loja para criar um setor', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListSectors.mockResolvedValue([])
    mockListStores.mockResolvedValue([{ id: 5, name: 'Loja Central', brand: null, active: true }])
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo setor/i }))
    expect(await screen.findByLabelText('Loja')).toBeRequired()
  })

  it('edita o nome de um setor existente', async () => {
    mockListSectors.mockResolvedValue([sector])
    mockUpdateSector.mockResolvedValueOnce({ ...sector, name: 'Nome Editado' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))

    const nameInput = screen.getByLabelText('Nome')
    await user.clear(nameInput)
    await user.type(nameInput, 'Nome Editado')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateSector).toHaveBeenCalledWith(sector.id, { name: 'Nome Editado' })
    })
  })

  it('ativa/desativa um setor direto na tabela', async () => {
    mockListSectors.mockResolvedValue([sector])
    mockUpdateSector.mockResolvedValueOnce({ ...sector, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Desativar' }))

    await waitFor(() => {
      expect(mockUpdateSector).toHaveBeenCalledWith(sector.id, { active: false })
    })
  })

  it('mostra o erro vindo da API quando a criação falha', async () => {
    mockListSectors.mockResolvedValue([])
    mockCreateSector.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Já existe um setor com esse nome.', code: 'CONFLICT' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo setor/i }))
    await user.type(screen.getByLabelText('Nome'), 'Repetido')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/já existe um setor/i)
  })

  // "Modo Deus" ---------------------------------------------------------------

  it('não mostra o botão "Excluir" para GESTOR', async () => {
    mockListSectors.mockResolvedValue([sector])
    renderPage()

    await screen.findByText('Cozinha Quente')
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
    mockListSectors.mockResolvedValue([sector])
    mockDeleteSector.mockResolvedValueOnce({ ...sector, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    expect(await screen.findByText('Excluir setor')).toBeInTheDocument()
    expect(mockDeleteSector).not.toHaveBeenCalled()

    const confirmButton = screen.getAllByRole('button', { name: 'Excluir' })[1]
    await user.click(confirmButton)

    await waitFor(() => expect(mockDeleteSector).toHaveBeenCalledWith(sector.id))
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
    mockListSectors.mockResolvedValue([sector])
    mockDeleteSector.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Setor não encontrado.', code: 'NOT_FOUND' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    await user.click(screen.getAllByRole('button', { name: 'Excluir' })[1])

    expect(await screen.findByRole('alert')).toHaveTextContent(/não encontrado/i)
  })
})
