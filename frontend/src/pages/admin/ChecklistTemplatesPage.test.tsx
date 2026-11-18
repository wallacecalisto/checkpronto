import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import { ChecklistTemplatesPage } from './ChecklistTemplatesPage'

const mockListChecklistTemplates = vi.fn()
const mockCreateChecklistTemplate = vi.fn()
const mockUpdateChecklistTemplate = vi.fn()
const mockDeleteChecklistTemplate = vi.fn()
const mockListStores = vi.fn()
const mockListSectors = vi.fn()

vi.mock('../../services/checklistTemplateService', () => ({
  listChecklistTemplates: (...args: unknown[]) => mockListChecklistTemplates(...args),
  createChecklistTemplate: (...args: unknown[]) => mockCreateChecklistTemplate(...args),
  updateChecklistTemplate: (...args: unknown[]) => mockUpdateChecklistTemplate(...args),
  deleteChecklistTemplate: (...args: unknown[]) => mockDeleteChecklistTemplate(...args),
}))

vi.mock('../../services/storeService', () => ({
  listStores: (...args: unknown[]) => mockListStores(...args),
}))

vi.mock('../../services/sectorService', () => ({
  listSectors: (...args: unknown[]) => mockListSectors(...args),
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

const template: ChecklistTemplate = {
  id: 1,
  store_id: 1,
  name: 'Fechamento da cozinha',
  active: true,
  created_by_user_id: 1,
  target_sector_id: null,
  shift: 'Manhã',
  created_at: '2026-01-01T00:00:00Z',
  items: [
    {
      id: 1,
      template_id: 1,
      description: 'Desligar a fritadeira',
      order_index: 0,
      required: true,
      requires_photo: false,
      active: true,
    },
  ],
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/checklist-templates']}>
        <ChecklistTemplatesPage />
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ChecklistTemplatesPage', () => {
  beforeEach(() => {
    mockListChecklistTemplates.mockReset()
    mockCreateChecklistTemplate.mockReset()
    mockUpdateChecklistTemplate.mockReset()
    mockDeleteChecklistTemplate.mockReset()
    mockListStores.mockReset()
    mockListSectors.mockReset().mockResolvedValue([])
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

  it('lista os checklists vindos da API', async () => {
    mockListChecklistTemplates.mockResolvedValueOnce([template])
    renderPage()

    expect(await screen.findByText('Fechamento da cozinha')).toBeInTheDocument()
    expect(screen.getByText('1 ativo(s)')).toBeInTheDocument()
    expect(screen.getByText('Ativo')).toBeInTheDocument()
  })

  it('esconde checklists inativos até marcar "Mostrar inativos"', async () => {
    mockListChecklistTemplates.mockResolvedValueOnce([{ ...template, id: 2, name: 'Desligado', active: false }])
    const user = userEvent.setup()
    renderPage()

    await waitFor(() => expect(mockListChecklistTemplates).toHaveBeenCalled())
    expect(screen.queryByText('Desligado')).not.toBeInTheDocument()

    await user.click(screen.getByLabelText(/mostrar inativos/i))
    expect(await screen.findByText('Desligado')).toBeInTheDocument()
  })

  it('cria um checklist com itens (GESTOR, sem seletor de loja)', async () => {
    mockListChecklistTemplates.mockResolvedValue([])
    mockCreateChecklistTemplate.mockResolvedValueOnce({ ...template, id: 2, name: 'Novo Checklist' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo checklist/i }))
    expect(screen.queryByLabelText('Loja')).not.toBeInTheDocument()

    await user.type(screen.getByLabelText('Nome'), 'Novo Checklist')
    await user.type(screen.getByPlaceholderText(/desligar a fritadeira/i), 'Trancar a porta')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateChecklistTemplate).toHaveBeenCalledWith({
        name: 'Novo Checklist',
        store_id: undefined,
        target_sector_id: undefined,
        shift: 'Manhã',
        items: [{ description: 'Trancar a porta', order_index: 0, required: true, requires_photo: false }],
      })
    })
  })

  it('cria um checklist com turno e item exigindo foto', async () => {
    mockListChecklistTemplates.mockResolvedValue([])
    mockCreateChecklistTemplate.mockResolvedValueOnce({ ...template, id: 5, name: 'Com Turno e Foto' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo checklist/i }))
    const shiftSelect = await screen.findByLabelText(/turno/i)
    expect(within(shiftSelect).getByRole('option', { name: 'Manhã' })).toBeInTheDocument()
    expect(within(shiftSelect).queryByRole('option', { name: /sem turno/i })).not.toBeInTheDocument()
    expect(shiftSelect).toBeRequired()

    await user.type(screen.getByLabelText('Nome'), 'Com Turno e Foto')
    await user.type(screen.getByPlaceholderText(/desligar a fritadeira/i), 'Foto da geladeira')
    await user.selectOptions(shiftSelect, 'Manhã')
    await user.click(screen.getByLabelText('Exige foto'))
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateChecklistTemplate).toHaveBeenCalledWith(
        expect.objectContaining({
          shift: 'Manhã',
          items: [{ description: 'Foto da geladeira', order_index: 0, required: true, requires_photo: true }],
        }),
      )
    })
  })

  it('cria um checklist com setor selecionado (visível no tablet daquele setor)', async () => {
    mockListChecklistTemplates.mockResolvedValue([])
    mockListSectors.mockResolvedValue([{ id: 9, store_id: 1, name: 'Cozinha Quente', active: true }])
    mockCreateChecklistTemplate.mockResolvedValueOnce({ ...template, id: 3, name: 'Checklist Setorial' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo checklist/i }))
    await user.type(screen.getByLabelText('Nome'), 'Checklist Setorial')
    await user.type(screen.getByPlaceholderText(/desligar a fritadeira/i), 'Trancar a porta')
    await user.selectOptions(await screen.findByLabelText('Setor'), 'Cozinha Quente')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockCreateChecklistTemplate).toHaveBeenCalledWith({
        name: 'Checklist Setorial',
        store_id: undefined,
        target_sector_id: 9,
        shift: 'Manhã',
        items: [{ description: 'Trancar a porta', order_index: 0, required: true, requires_photo: false }],
      })
    })
  })

  it('MASTER precisa escolher uma loja para criar um checklist', async () => {
    mockUser = {
      id: 1,
      name: 'Master',
      email: 'master@kijapa.com',
      role: 'MASTER',
      store_id: null,
      active: true,
      must_change_password: false,
    }
    mockListChecklistTemplates.mockResolvedValue([])
    mockListStores.mockResolvedValue([{ id: 5, name: 'Loja Central', brand: null, active: true }])
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo checklist/i }))
    expect(await screen.findByLabelText('Loja')).toBeRequired()
  })

  it('não permite salvar sem pelo menos um item preenchido', async () => {
    mockListChecklistTemplates.mockResolvedValue([])
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo checklist/i }))
    await user.type(screen.getByLabelText('Nome'), 'Checklist Vazio')

    expect(screen.getByRole('button', { name: 'Salvar' })).toBeDisabled()
  })

  it('edita o nome de um checklist existente', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockUpdateChecklistTemplate.mockResolvedValueOnce({ ...template, name: 'Nome Editado' })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))
    const nameInput = screen.getByLabelText('Nome')
    await user.clear(nameInput)
    await user.type(nameInput, 'Nome Editado')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateChecklistTemplate).toHaveBeenCalledWith(template.id, {
        name: 'Nome Editado',
        target_sector_id: null,
        shift: 'Manhã',
      })
    })
  })

  it('ativa/desativa um checklist direto na tabela', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    mockUpdateChecklistTemplate.mockResolvedValueOnce({ ...template, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Desativar' }))

    await waitFor(() => {
      expect(mockUpdateChecklistTemplate).toHaveBeenCalledWith(template.id, { active: false })
    })
  })

  it('mostra o erro vindo da API quando a criação falha', async () => {
    mockListChecklistTemplates.mockResolvedValue([])
    mockCreateChecklistTemplate.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Já existe um checklist com esse nome.', code: 'CONFLICT' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: /novo checklist/i }))
    await user.type(screen.getByLabelText('Nome'), 'Checklist X')
    await user.type(screen.getByPlaceholderText(/desligar a fritadeira/i), 'Item X')
    await user.click(screen.getByRole('button', { name: 'Salvar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/já existe um checklist/i)
  })

  // "Modo Deus" --------------------------------------------------

  it('não mostra o botão "Excluir" para GESTOR', async () => {
    mockListChecklistTemplates.mockResolvedValue([template])
    renderPage()

    await screen.findByText('Fechamento da cozinha')
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
    mockListChecklistTemplates.mockResolvedValue([template])
    mockDeleteChecklistTemplate.mockResolvedValueOnce({ ...template, active: false })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    expect(await screen.findByText('Excluir checklist')).toBeInTheDocument()
    expect(mockDeleteChecklistTemplate).not.toHaveBeenCalled()

    const confirmButton = screen.getAllByRole('button', { name: 'Excluir' })[1]
    await user.click(confirmButton)

    await waitFor(() => expect(mockDeleteChecklistTemplate).toHaveBeenCalledWith(template.id))
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
    mockListChecklistTemplates.mockResolvedValue([template])
    mockDeleteChecklistTemplate.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Template não encontrado.', code: 'NOT_FOUND' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Excluir' }))
    await user.click(screen.getAllByRole('button', { name: 'Excluir' })[1])

    expect(await screen.findByRole('alert')).toHaveTextContent(/não encontrado/i)
  })
})
