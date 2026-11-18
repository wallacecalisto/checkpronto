import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../../types/auth'
import type { ChecklistExecution } from '../../types/checklistExecution'
import { ChecklistExecutionDetailPage } from './ChecklistExecutionDetailPage'

const mockGetChecklistExecution = vi.fn()
const mockAnswerChecklistItem = vi.fn()
const mockCompleteChecklistExecution = vi.fn()
const mockValidateChecklistItem = vi.fn()

vi.mock('../../services/checklistService', () => ({
  getChecklistExecution: (...args: unknown[]) => mockGetChecklistExecution(...args),
  answerChecklistItem: (...args: unknown[]) => mockAnswerChecklistItem(...args),
  completeChecklistExecution: (...args: unknown[]) => mockCompleteChecklistExecution(...args),
  validateChecklistItem: (...args: unknown[]) => mockValidateChecklistItem(...args),
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

const EXECUTOR_ID = 42

function buildExecution(): ChecklistExecution {
  return {
    id: 1,
    template_id: 1,
    template_name: 'Abertura da Cozinha',
    store_id: 1,
    shift: 'MANHA',
    executed_by_user_id: EXECUTOR_ID,
    executed_by_employee_id: null,
    executed_by_name: 'Executor Teste',
    validated_by_names: [],
    started_at: '2026-09-11T09:00:00Z',
    finished_at: '2026-09-11T09:20:00Z',
    status: 'COMPLETED',
    fully_validated: false,
    items: [
      {
        id: 100,
        checklist_execution_id: 1,
        template_item_id: 10,
        item_description_snapshot: 'Verificar temperatura da geladeira',
        response: 'OK',
        observation: null,
        photo_url: null,
        extra_photo_urls: [],
        requires_photo: false,
        validation: null,
      },
    ],
  }
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/checklists/1']}>
        <Routes>
          <Route path="/admin/checklists/:id" element={<ChecklistExecutionDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ChecklistExecutionDetailPage', () => {
  beforeEach(() => {
    mockGetChecklistExecution.mockReset().mockResolvedValue(buildExecution())
    mockAnswerChecklistItem.mockReset()
    mockCompleteChecklistExecution.mockReset()
    mockValidateChecklistItem.mockReset()
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

  it('quando o usuário logado é quem executou o checklist, não mostra "Validar" e explica o motivo', async () => {
    mockUser = { ...mockUser, id: EXECUTOR_ID }
    renderPage()

    await screen.findByText('Verificar temperatura da geladeira')

    expect(screen.queryByRole('button', { name: 'Validar' })).not.toBeInTheDocument()
    expect(
      screen.getByText(
        /Aguardando validação de outro gestor ou líder — quem executou o checklist não pode validar seus próprios itens\./,
      ),
    ).toBeInTheDocument()
  })

  it('quando o usuário logado é diferente de quem executou, mostra "Validar" e revela Aprovar/Divergente ao clicar', async () => {
    mockUser = { ...mockUser, id: 999 }
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Verificar temperatura da geladeira')

    const validarButton = screen.getByRole('button', { name: 'Validar' })
    await user.click(validarButton)

    expect(screen.getByRole('button', { name: 'Aprovar' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Divergente' })).toBeInTheDocument()
    expect(screen.getByRole('button', { name: 'Confirmar' })).toBeInTheDocument()
  })

  it('mostra mensagem específica quando a validação falha com SAME_USER_VALIDATION_FORBIDDEN', async () => {
    mockUser = { ...mockUser, id: 999 }
    mockValidateChecklistItem.mockRejectedValue({
      isAxiosError: true,
      response: { data: { detail: 'erro', code: 'SAME_USER_VALIDATION_FORBIDDEN' } },
    })
    const user = userEvent.setup()
    renderPage()

    await screen.findByText('Verificar temperatura da geladeira')

    await user.click(screen.getByRole('button', { name: 'Validar' }))
    await user.click(screen.getByRole('button', { name: 'Confirmar' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(
      'Quem executou o checklist não pode validar seus próprios itens.',
    )
  })


  it('mostra a miniatura da foto quando o item tem photo_url', async () => {
    const execution = buildExecution()
    execution.items[0].photo_url = 'https://cdn.example.com/foto.jpg'
    execution.items[0].requires_photo = true
    mockGetChecklistExecution.mockReset().mockResolvedValue(execution)
    renderPage()

    const image = await screen.findByRole('img', { name: 'Foto enviada pelo operador 1' })
    expect(image).toHaveAttribute('src', 'https://cdn.example.com/foto.jpg')
  })

  it('não mostra miniatura quando o item não tem photo_url', async () => {
    renderPage()

    await screen.findByText('Verificar temperatura da geladeira')
    expect(screen.queryByRole('img', { name: /Foto enviada pelo operador/ })).not.toBeInTheDocument()
  })

  it('mostra uma miniatura por foto do item', async () => {
    const execution = buildExecution()
    execution.items[0].photo_url = 'https://cdn.example.com/foto1.jpg'
    execution.items[0].extra_photo_urls = ['https://cdn.example.com/foto2.jpg']
    execution.items[0].requires_photo = true
    mockGetChecklistExecution.mockReset().mockResolvedValue(execution)
    renderPage()

    expect(await screen.findByRole('img', { name: 'Foto enviada pelo operador 1' })).toHaveAttribute(
      'src',
      'https://cdn.example.com/foto1.jpg',
    )
    expect(screen.getByRole('img', { name: 'Foto enviada pelo operador 2' })).toHaveAttribute(
      'src',
      'https://cdn.example.com/foto2.jpg',
    )
  })


  it('clicar na miniatura abre o lightbox ampliado; "X" fecha', async () => {
    const execution = buildExecution()
    execution.items[0].photo_url = 'https://cdn.example.com/foto.jpg'
    execution.items[0].requires_photo = true
    mockGetChecklistExecution.mockReset().mockResolvedValue(execution)
    const user = userEvent.setup()
    renderPage()

    const thumbnail = await screen.findByRole('img', { name: 'Foto enviada pelo operador 1' })
    await user.click(thumbnail)

    const lightboxImage = screen.getByRole('img', { name: 'Foto enviada pelo operador' })
    expect(lightboxImage).toHaveAttribute('src', 'https://cdn.example.com/foto.jpg')

    await user.click(screen.getByRole('button', { name: 'Fechar' }))
    expect(screen.queryByRole('img', { name: 'Foto enviada pelo operador' })).not.toBeInTheDocument()
  })
})
