import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import { useEffect } from 'react'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SelectedStoreProvider, useSelectedStore } from '../../contexts/SelectedStoreContext'
import type { User } from '../../types/auth'
import { Header } from './Header'

const mockGetStore = vi.fn()
const mockListStores = vi.fn()

vi.mock('../../services/storeService', () => ({
  getStore: (...args: unknown[]) => mockGetStore(...args),
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

function Selector({ storeId }: { storeId: number | null }) {
  const { setStoreId } = useSelectedStore()
  useEffect(() => {
    setStoreId(storeId)
  }, [storeId, setStoreId])
  return null
}

function renderHeader(selectedStoreId: number | null = null) {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <SelectedStoreProvider>
        <Selector storeId={selectedStoreId} />
        <Header />
      </SelectedStoreProvider>
    </QueryClientProvider>,
  )
}

// o header mostra o nome da loja em destaque (badge), sem
// nenhuma imagem — reverte a logo de co-branding
describe('Header', () => {
  beforeEach(() => {
    mockGetStore.mockReset()
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

  it('mostra o nome do usuário e o papel', async () => {
    mockGetStore.mockResolvedValue({ id: 1, name: 'Cozinha Pinheiros', brand: null, active: true })
    renderHeader()

    expect(await screen.findByText('Gestora')).toBeInTheDocument()
    expect(screen.getByText('GESTOR')).toBeInTheDocument()
  })

  it('GESTOR/LIDER veem o nome da própria loja em destaque', async () => {
    mockGetStore.mockResolvedValue({ id: 1, name: 'Cozinha Pinheiros', brand: null, active: true })
    renderHeader()

    expect(await screen.findByText('Cozinha Pinheiros')).toBeInTheDocument()
    expect(mockGetStore).toHaveBeenCalledWith(1)
  })

  it('MASTER sem loja selecionada vê "Todas as lojas"', async () => {
    mockUser = { ...mockUser, role: 'MASTER', store_id: null }
    renderHeader(null)

    expect(await screen.findByText('Todas as lojas')).toBeInTheDocument()
    expect(mockGetStore).not.toHaveBeenCalled()
  })

  it('MASTER com loja selecionada no seletor do Painel vê o nome dela no header', async () => {
    mockUser = { ...mockUser, role: 'MASTER', store_id: null }
    mockListStores.mockResolvedValue([
      { id: 1, name: 'Cozinha Pinheiros', brand: null, active: true },
      { id: 2, name: 'Cozinha Centro', brand: null, active: true },
    ])
    renderHeader(2)

    expect(await screen.findByText('Cozinha Centro')).toBeInTheDocument()
    expect(screen.queryByText('Todas as lojas')).not.toBeInTheDocument()
  })
})
