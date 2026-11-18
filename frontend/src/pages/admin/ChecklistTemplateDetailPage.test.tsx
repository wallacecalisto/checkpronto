import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor, within } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { ChecklistTemplate } from '../../types/checklistTemplate'
import { ChecklistTemplateDetailPage } from './ChecklistTemplateDetailPage'

const mockGetChecklistTemplate = vi.fn()
const mockCreateChecklistTemplateItem = vi.fn()
const mockUpdateChecklistTemplateItem = vi.fn()

vi.mock('../../services/checklistTemplateService', () => ({
  getChecklistTemplate: (...args: unknown[]) => mockGetChecklistTemplate(...args),
  createChecklistTemplateItem: (...args: unknown[]) => mockCreateChecklistTemplateItem(...args),
  updateChecklistTemplateItem: (...args: unknown[]) => mockUpdateChecklistTemplateItem(...args),
}))

function buildTemplate(): ChecklistTemplate {
  return {
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
        id: 10,
        template_id: 1,
        description: 'Trancar a porta dos fundos',
        order_index: 1,
        required: true,
        requires_photo: false,
        active: true,
      },
    ],
  }
}

function renderPage() {
  const queryClient = new QueryClient()
  return render(
    <QueryClientProvider client={queryClient}>
      <MemoryRouter initialEntries={['/admin/checklist-templates/1']}>
        <Routes>
          <Route path="/admin/checklist-templates/:id" element={<ChecklistTemplateDetailPage />} />
        </Routes>
      </MemoryRouter>
    </QueryClientProvider>,
  )
}

describe('ChecklistTemplateDetailPage', () => {
  beforeEach(() => {
    mockGetChecklistTemplate.mockReset().mockResolvedValue(buildTemplate())
    mockCreateChecklistTemplateItem.mockReset()
    mockUpdateChecklistTemplateItem.mockReset()
  })

  it('cria um item novo marcando "Exige foto"', async () => {
    mockCreateChecklistTemplateItem.mockResolvedValueOnce({
      id: 11,
      template_id: 1,
      description: 'Guardar os alimentos',
      order_index: 2,
      required: true,
      requires_photo: true,
      active: true,
    })
    const user = userEvent.setup()
    renderPage()

    await user.type(await screen.findByLabelText('Novo item'), 'Guardar os alimentos')
    await user.click(screen.getByRole('checkbox', { name: 'Exige foto' }))
    await user.click(screen.getByRole('button', { name: 'Adicionar' }))

    await waitFor(() => {
      expect(mockCreateChecklistTemplateItem).toHaveBeenCalledWith(1, {
        description: 'Guardar os alimentos',
        order_index: 2,
        required: true,
        requires_photo: true,
      })
    })
  })

  it('a tabela mostra a coluna "Foto" com o estado atual do item', async () => {
    renderPage()

    expect(await screen.findByText('Trancar a porta dos fundos')).toBeInTheDocument()
    const row = screen.getByText('Trancar a porta dos fundos').closest('tr')!
    expect(row).toHaveTextContent('Não')
  })

  it('edita um item existente para marcar "Exige foto"', async () => {
    mockUpdateChecklistTemplateItem.mockResolvedValueOnce({
      id: 10,
      template_id: 1,
      description: 'Trancar a porta dos fundos',
      order_index: 1,
      required: true,
      requires_photo: true,
      active: true,
    })
    const user = userEvent.setup()
    renderPage()

    await user.click(await screen.findByRole('button', { name: 'Editar' }))
    const editRow = screen.getByRole('button', { name: 'Salvar' }).closest('tr')!
    await user.click(within(editRow).getByRole('checkbox', { name: 'Exige foto' }))
    await user.click(within(editRow).getByRole('button', { name: 'Salvar' }))

    await waitFor(() => {
      expect(mockUpdateChecklistTemplateItem).toHaveBeenCalledWith(10, {
        description: 'Trancar a porta dos fundos',
        required: true,
        requires_photo: true,
      })
    })
  })
})
