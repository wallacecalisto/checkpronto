import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { SelectedStoreProvider } from '../../contexts/SelectedStoreContext'
import type { User } from '../../types/auth'
import type { StoreSettings } from '../../types/storeSettings'
import { StoreSettingsPage } from './StoreSettingsPage'

const mockGetStoreSettings = vi.fn()
const mockUpdateStoreSettings = vi.fn()
const mockListStores = vi.fn()

vi.mock('../../services/storeSettingsService', () => ({
  getStoreSettings: (...args: unknown[]) => mockGetStoreSettings(...args),
  updateStoreSettings: (...args: unknown[]) => mockUpdateStoreSettings(...args),
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

const defaultSettings: StoreSettings = {
  store_id: 1,
  max_assignees_per_task: null,
  operational_checklists_enabled: true,
  auto_logout_minutes: 5,
  hide_task_timer: false,
  require_live_photo_only: false,
  require_pin_on_complete: false,
  enable_audio_alerts: false,
  shifts: ['Manhã', 'Tarde', 'Noite'],
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <SelectedStoreProvider>
        <StoreSettingsPage />
      </SelectedStoreProvider>
    </QueryClientProvider>,
  )
}

describe('StoreSettingsPage', () => {
  beforeEach(() => {
    mockGetStoreSettings.mockReset()
    mockUpdateStoreSettings.mockReset()
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

  it('GESTOR vê e edita direto as configurações da própria loja, sem seletor', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    renderPage()

    expect(await screen.findByLabelText(/limite de pessoas por tarefa/i)).toHaveValue(null)
    expect(screen.queryByText('Selecione uma loja…')).not.toBeInTheDocument()
    await waitFor(() => expect(mockGetStoreSettings).toHaveBeenCalledWith(1))
  })

  it('divide as configurações em 3 seções', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    renderPage()

    await screen.findByLabelText(/limite de pessoas por tarefa/i)
    expect(screen.getByText('Regras de Operação')).toBeInTheDocument()
    expect(screen.getByText('Interface e Notificações')).toBeInTheDocument()
    expect(screen.getByText('Auditoria e Segurança')).toBeInTheDocument()
  })

  it('nunca usa a palavra "tablet" — o sistema roda em qualquer dispositivo', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    const { container } = renderPage()

    await screen.findByLabelText(/limite de pessoas por tarefa/i)
    expect(container.textContent).not.toMatch(/tablet/i)
  })

  it('preenche o formulário com os valores atuais vindos da API', async () => {
    mockGetStoreSettings.mockResolvedValue({
      store_id: 1,
      max_assignees_per_task: 2,
      operational_checklists_enabled: false,
      auto_logout_minutes: 10,
      hide_task_timer: true,
      require_live_photo_only: true,
      require_pin_on_complete: true,
      enable_audio_alerts: true,
      shifts: ['Abertura', 'Fechamento'],
    })
    renderPage()

    expect(await screen.findByLabelText(/limite de pessoas por tarefa/i)).toHaveValue(2)
    expect(screen.getByLabelText(/tempo de auto-logout/i)).toHaveValue(10)
    expect(screen.getByLabelText(/habilitar checklists no operacional/i)).not.toBeChecked()
    expect(screen.getByLabelText(/ocultar cronômetro/i)).toBeChecked()
    expect(screen.getByLabelText(/apenas foto tirada na hora/i)).toBeChecked()
    expect(screen.getByLabelText(/exigir pin na conclusão/i)).toBeChecked()
    expect(screen.getByLabelText(/alertas sonoros/i)).toBeChecked()
  })

  it('usa switches estilizados (role="switch"), não checkboxes nativos visíveis', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    renderPage()

    expect((await screen.findAllByRole('switch')).length).toBe(5)
  })

  it('salva o formulário chamando updateStoreSettings com os valores corretos', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    mockUpdateStoreSettings.mockResolvedValueOnce({
      ...defaultSettings,
      max_assignees_per_task: 1,
      operational_checklists_enabled: false,
    })
    const user = userEvent.setup()
    renderPage()

    const maxAssigneesInput = await screen.findByLabelText(/limite de pessoas por tarefa/i)
    await user.clear(maxAssigneesInput)
    await user.type(maxAssigneesInput, '1')
    await user.click(screen.getByLabelText(/habilitar checklists no operacional/i))
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateStoreSettings).toHaveBeenCalledWith(1, {
        max_assignees_per_task: 1,
        operational_checklists_enabled: false,
        auto_logout_minutes: 5,
        hide_task_timer: false,
        enable_audio_alerts: false,
        require_live_photo_only: false,
        require_pin_on_complete: false,
        shifts: ['Manhã', 'Tarde', 'Noite'],
      })
    })
    expect(await screen.findByText('Configurações salvas.')).toBeInTheDocument()
  })

  it('campo vazio de limite de pessoas salva como null (ilimitado)', async () => {
    mockGetStoreSettings.mockResolvedValue({ ...defaultSettings, max_assignees_per_task: 2 })
    mockUpdateStoreSettings.mockResolvedValueOnce(defaultSettings)
    const user = userEvent.setup()
    renderPage()

    const maxAssigneesInput = await screen.findByLabelText(/limite de pessoas por tarefa/i)
    await user.clear(maxAssigneesInput)
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateStoreSettings).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ max_assignees_per_task: null }),
      )
    })
  })

  it('envia todos os novos campos operacionais quando alterados', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    mockUpdateStoreSettings.mockResolvedValueOnce(defaultSettings)
    const user = userEvent.setup()
    renderPage()

    const autoLogoutInput = await screen.findByLabelText(/tempo de auto-logout/i)
    await user.clear(autoLogoutInput)
    await user.type(autoLogoutInput, '15')
    await user.click(screen.getByLabelText(/ocultar cronômetro/i))
    await user.click(screen.getByLabelText(/apenas foto tirada na hora/i))
    await user.click(screen.getByLabelText(/exigir pin na conclusão/i))
    await user.click(screen.getByLabelText(/alertas sonoros/i))
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateStoreSettings).toHaveBeenCalledWith(
        1,
        expect.objectContaining({
          auto_logout_minutes: 15,
          hide_task_timer: true,
          require_live_photo_only: true,
          require_pin_on_complete: true,
          enable_audio_alerts: true,
        }),
      )
    })
  })


  it('mostra os turnos atuais e permite adicionar um novo', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    mockUpdateStoreSettings.mockResolvedValueOnce({ ...defaultSettings, shifts: ['Manhã', 'Tarde', 'Noite', 'Madrugada'] })
    const user = userEvent.setup()
    renderPage()

    expect(await screen.findByText('Manhã')).toBeInTheDocument()
    expect(screen.getByText('Tarde')).toBeInTheDocument()
    expect(screen.getByText('Noite')).toBeInTheDocument()

    await user.type(screen.getByLabelText('Novo turno'), 'Madrugada')
    await user.click(screen.getByRole('button', { name: 'Adicionar' }))
    expect(screen.getByText('Madrugada')).toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateStoreSettings).toHaveBeenCalledWith(
        1,
        expect.objectContaining({ shifts: ['Manhã', 'Tarde', 'Noite', 'Madrugada'] }),
      )
    })
  })

  it('remove um turno clicando no X', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    mockUpdateStoreSettings.mockResolvedValueOnce({ ...defaultSettings, shifts: ['Manhã', 'Noite'] })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Tarde')
    await user.click(screen.getByRole('button', { name: 'Remover turno Tarde' }))
    expect(screen.queryByText('Tarde')).not.toBeInTheDocument()

    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateStoreSettings).toHaveBeenCalledWith(1, expect.objectContaining({ shifts: ['Manhã', 'Noite'] }))
    })
  })

  it('não permite remover o último turno restante', async () => {
    mockGetStoreSettings.mockResolvedValue({ ...defaultSettings, shifts: ['Único'] })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Único')
    const removeButton = screen.getByRole('button', { name: 'Remover turno Único' })
    expect(removeButton).toBeDisabled()

    await user.click(removeButton)
    expect(screen.getByText('Único')).toBeInTheDocument()
  })

  it('não duplica um turno já existente', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Manhã')
    await user.type(screen.getByLabelText('Novo turno'), 'Manhã')
    await user.click(screen.getByRole('button', { name: 'Adicionar' }))

    expect(screen.getAllByText('Manhã')).toHaveLength(1)
  })

  it('mostra o erro vindo da API quando salvar falha', async () => {
    mockGetStoreSettings.mockResolvedValue(defaultSettings)
    mockUpdateStoreSettings.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Você não tem permissão para acessar este recurso.', code: 'FORBIDDEN' } },
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByLabelText(/limite de pessoas por tarefa/i)
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/não tem permissão/i)
  })

  it('MASTER precisa escolher uma loja antes de ver o formulário', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListStores.mockResolvedValue([{ id: 5, name: 'Loja Central', brand: null, active: true }])
    renderPage()

    expect(await screen.findByText(/selecione uma loja acima/i)).toBeInTheDocument()
    expect(mockGetStoreSettings).not.toHaveBeenCalled()
  })

  it('MASTER escolhe uma loja no seletor e o formulário carrega as configurações dela', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListStores.mockResolvedValue([{ id: 5, name: 'Loja Central', brand: null, active: true }])
    mockGetStoreSettings.mockResolvedValue({ ...defaultSettings, store_id: 5 })
    const user = userEvent.setup()
    renderPage()

    await screen.findByRole('option', { name: 'Loja Central' })
    await user.selectOptions(screen.getByRole('combobox'), '5')

    await waitFor(() => expect(mockGetStoreSettings).toHaveBeenCalledWith(5))
  })
})
