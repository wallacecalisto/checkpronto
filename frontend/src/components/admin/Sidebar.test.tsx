import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import { Sidebar } from './Sidebar'

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

function renderSidebar() {
  return render(
    <MemoryRouter initialEntries={['/admin']}>
      <Sidebar />
    </MemoryRouter>,
  )
}

describe('Sidebar', () => {
  beforeEach(() => {
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

  it('GESTOR: vê as seções e rótulos renomeados, mas não os itens exclusivos de MASTER', () => {
    renderSidebar()

    expect(screen.getByText('Painel')).toBeInTheDocument()

    expect(screen.getByText('Tarefas')).toBeInTheDocument()
    expect(screen.getByText('Checklists')).toBeInTheDocument()
    expect(screen.getByText('Administração')).toBeInTheDocument()

    expect(screen.getByText('Catálogo de Tarefas')).toBeInTheDocument()
    expect(screen.getByText('Agendamento de Tarefas')).toBeInTheDocument()
    expect(screen.getByText('Execuções de Checklists')).toBeInTheDocument()
    expect(screen.getByText('Catálogo de Checklists')).toBeInTheDocument()

    expect(screen.getByText('Setores')).toBeInTheDocument()
    expect(screen.getByText('Funcionários')).toBeInTheDocument()
    expect(screen.getByText('Logs')).toBeInTheDocument()

    expect(screen.queryByText('Lojas')).not.toBeInTheDocument()
    expect(screen.queryByText('Usuários')).not.toBeInTheDocument()
  })

  it('LIDER: não vê itens exclusivos de MASTER/GESTOR, mas vê "Catálogo de Checklists"', () => {
    mockUser = { ...mockUser, role: 'LIDER' }
    renderSidebar()

    expect(screen.queryByText('Lojas')).not.toBeInTheDocument()
    expect(screen.queryByText('Usuários')).not.toBeInTheDocument()
    expect(screen.queryByText('Logs')).not.toBeInTheDocument()

    expect(screen.getByText('Administração')).toBeInTheDocument()
    expect(screen.getByText('Setores')).toBeInTheDocument()
    expect(screen.getByText('Funcionários')).toBeInTheDocument()

    expect(screen.getByText('Checklists')).toBeInTheDocument()
    expect(screen.getByText('Execuções de Checklists')).toBeInTheDocument()
    expect(screen.getByText('Catálogo de Checklists')).toBeInTheDocument()
  })

  it('MASTER: vê todos os itens, incluindo "Lojas" e "Usuários"', () => {
    mockUser = { ...mockUser, role: 'MASTER', store_id: null }
    renderSidebar()

    expect(screen.getByText('Painel')).toBeInTheDocument()
    expect(screen.getByText('Tarefas')).toBeInTheDocument()
    expect(screen.getByText('Checklists')).toBeInTheDocument()
    expect(screen.getByText('Administração')).toBeInTheDocument()

    expect(screen.getByText('Catálogo de Tarefas')).toBeInTheDocument()
    expect(screen.getByText('Agendamento de Tarefas')).toBeInTheDocument()
    expect(screen.getByText('Execuções de Checklists')).toBeInTheDocument()
    expect(screen.getByText('Catálogo de Checklists')).toBeInTheDocument()
    expect(screen.getByText('Setores')).toBeInTheDocument()
    expect(screen.getByText('Funcionários')).toBeInTheDocument()
    expect(screen.getByText('Lojas')).toBeInTheDocument()
    expect(screen.getByText('Usuários')).toBeInTheDocument()
    expect(screen.getByText('Logs')).toBeInTheDocument()
  })
})
