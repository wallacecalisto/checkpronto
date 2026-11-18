import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { EmployeeListModal } from './EmployeeListModal'

const mockListEmployees = vi.fn()

vi.mock('../../services/employeeService', () => ({
  listEmployees: (...args: unknown[]) => mockListEmployees(...args),
}))

function renderModal(props: Partial<Parameters<typeof EmployeeListModal>[0]> = {}) {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <EmployeeListModal onSelectEmployee={vi.fn()} onClose={vi.fn()} {...props} />
    </QueryClientProvider>,
  )
}

describe('EmployeeListModal', () => {
  beforeEach(() => {
    mockListEmployees.mockReset()
  })

  it('busca só funcionários ativos, filtrados pela loja informada', async () => {
    mockListEmployees.mockResolvedValue([])
    renderModal({ storeId: 7 })

    await screen.findByText('Nenhum funcionário ativo cadastrado.')
    expect(mockListEmployees).toHaveBeenCalledWith({ activeOnly: true, storeId: 7 })
  })

  it('lista os funcionários retornados, com cargo quando presente', async () => {
    mockListEmployees.mockResolvedValue([
      { id: 1, store_id: 1, name: 'Ana Souza', role_title: 'Cozinheira', active: true, has_pin: true },
      { id: 2, store_id: 1, name: 'Bruno Lima', role_title: null, active: true, has_pin: false },
    ])
    renderModal()

    expect(await screen.findByText('Ana Souza')).toBeInTheDocument()
    expect(screen.getByText('Cozinheira')).toBeInTheDocument()
    expect(screen.getByText('Bruno Lima')).toBeInTheDocument()
  })

  it('chama onSelectEmployee com id e nome ao clicar num funcionário', async () => {
    mockListEmployees.mockResolvedValue([
      { id: 5, store_id: 1, name: 'Carla Dias', role_title: null, active: true, has_pin: true },
    ])
    const onSelectEmployee = vi.fn()
    const user = userEvent.setup()
    renderModal({ onSelectEmployee })

    await user.click(await screen.findByText('Carla Dias'))

    expect(onSelectEmployee).toHaveBeenCalledWith({ id: 5, name: 'Carla Dias' })
  })
})
