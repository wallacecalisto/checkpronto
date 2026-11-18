import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { TaskExecutionTimeline } from '../../types/taskExecutionTimeline'
import { ExecutionTimelineModal } from './ExecutionTimelineModal'

const mockGetExecutionTimeline = vi.fn()

vi.mock('../../services/taskExecutionHistoryService', () => ({
  getExecutionTimeline: (...args: unknown[]) => mockGetExecutionTimeline(...args),
}))

const collaborativeTimeline: TaskExecutionTimeline = {
  execution_group_id: 'a1b2c3d4-0000-0000-0000-000000000000',
  task_id: 5,
  task_title: 'Fritar 200 empanados',
  created_by_user_name: 'Gestora Ana',
  estimated_duration_minutes: 20,
  started_at: '2026-09-23T12:00:00Z',
  completed_at: '2026-09-23T12:40:00Z',
  total_elapsed_seconds: 2400,
  result: 'FEITO',
  justification: null,
  observation: null,
  photo_url: null,
  extra_photo_urls: [],
  participants: [
    { employee_id: 1, employee_name: 'Carlos', worked_duration_seconds: 1200 },
    { employee_id: 2, employee_name: 'Bruna', worked_duration_seconds: 600 },
  ],
  sessions: [
    {
      employee_id: 1,
      employee_name: 'Carlos',
      started_at: '2026-09-23T12:00:00Z',
      ended_at: '2026-09-23T12:40:00Z',
      leave_reason: null,
    },
    {
      employee_id: 2,
      employee_name: 'Bruna',
      started_at: '2026-09-23T12:05:00Z',
      ended_at: '2026-09-23T12:15:00Z',
      leave_reason: 'Fui ajudar o caixa.',
    },
  ],
  blocks: [
    {
      blocked_by_employee_id: 1,
      blocked_by_employee_name: 'Carlos',
      reason: 'Faltou camarão no estoque.',
      started_at: '2026-09-23T12:20:00Z',
      ended_at: '2026-09-23T12:30:00Z',
    },
  ],
}

function renderModal(historyId = 42, onClose = vi.fn()) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <ExecutionTimelineModal historyId={historyId} onClose={onClose} />
    </QueryClientProvider>,
  )
  return { onClose }
}

describe('ExecutionTimelineModal', () => {
  it('mostra a anatomia completa de uma execução colaborativa', async () => {
    mockGetExecutionTimeline.mockResolvedValueOnce(collaborativeTimeline)
    renderModal()

    expect(await screen.findByText('Fritar 200 empanados')).toBeInTheDocument()
    expect(screen.getByText('Criada por Gestora Ana')).toBeInTheDocument()
    expect(screen.getByText('20min')).toBeInTheDocument()
    expect(screen.getByText('Feito')).toBeInTheDocument()

    // Participantes com o tempo trabalhado individual (nomes também
    // aparecem na linha do tempo abaixo, por isso getAllByText aqui).
    expect(screen.getAllByText('Carlos').length).toBeGreaterThan(0)
    expect(screen.getByText('20min trabalhados')).toBeInTheDocument()
    expect(screen.getAllByText('Bruna').length).toBeGreaterThan(0)
    expect(screen.getByText('10min trabalhados')).toBeInTheDocument()

    // Sessão com motivo de saída.
    expect(screen.getByText(/Fui ajudar o caixa/)).toBeInTheDocument()

    // Período de impedimento, com quem reportou e o motivo.
    expect(screen.getByText(/reportou impedimento/)).toBeInTheDocument()
    expect(screen.getByText(/Faltou camarão no estoque/)).toBeInTheDocument()
    expect(screen.getByText(/Retomada às/)).toBeInTheDocument()

    expect(mockGetExecutionTimeline).toHaveBeenCalledWith(42)
  })

  it('mostra a execução individual sem impedimentos', async () => {
    mockGetExecutionTimeline.mockResolvedValueOnce({
      ...collaborativeTimeline,
      participants: [{ employee_id: 1, employee_name: 'Carlos', worked_duration_seconds: 2400 }],
      sessions: [
        {
          employee_id: 1,
          employee_name: 'Carlos',
          started_at: '2026-09-23T12:00:00Z',
          ended_at: '2026-09-23T12:40:00Z',
          leave_reason: null,
        },
      ],
      blocks: [],
    })
    renderModal()

    expect(await screen.findByText('Fritar 200 empanados')).toBeInTheDocument()
    expect(screen.queryByText(/reportou impedimento/)).not.toBeInTheDocument()
  })


  it('clicar na miniatura da foto abre o lightbox ampliado; "X" fecha', async () => {
    mockGetExecutionTimeline.mockResolvedValueOnce({
      ...collaborativeTimeline,
      photo_url: 'https://cdn.example.com/empanados.jpg',
    })
    const user = userEvent.setup()
    renderModal()

    const thumbnail = await screen.findByAltText('Comprovação da conclusão 1')
    await user.click(thumbnail)

    const lightboxImage = screen.getByAltText('Comprovação da conclusão')
    expect(lightboxImage).toHaveAttribute('src', 'https://cdn.example.com/empanados.jpg')

    // O modal por trás também tem botões "Fechar" (cabeçalho e rodapé) — o
    // do lightbox é o último a entrar no DOM.
    const fecharButtons = screen.getAllByRole('button', { name: 'Fechar' })
    await user.click(fecharButtons[fecharButtons.length - 1])
    expect(screen.queryByAltText('Comprovação da conclusão')).not.toBeInTheDocument()
  })

  it('mostra uma miniatura por foto (photo_url + extra_photo_urls)', async () => {
    mockGetExecutionTimeline.mockResolvedValueOnce({
      ...collaborativeTimeline,
      photo_url: 'https://cdn.example.com/foto1.jpg',
      extra_photo_urls: ['https://cdn.example.com/foto2.jpg', 'https://cdn.example.com/foto3.jpg'],
    })
    renderModal()

    expect(await screen.findByAltText('Comprovação da conclusão 1')).toHaveAttribute(
      'src',
      'https://cdn.example.com/foto1.jpg',
    )
    expect(screen.getByAltText('Comprovação da conclusão 2')).toHaveAttribute('src', 'https://cdn.example.com/foto2.jpg')
    expect(screen.getByAltText('Comprovação da conclusão 3')).toHaveAttribute('src', 'https://cdn.example.com/foto3.jpg')
  })


  it('evidencia um "Período Ocioso" quando há um buraco sem sessão nem impedimento', async () => {
    mockGetExecutionTimeline.mockResolvedValueOnce({
      ...collaborativeTimeline,
      started_at: '2026-09-23T12:00:00Z',
      completed_at: '2026-09-23T12:40:00Z',
      sessions: [
        {
          employee_id: 1,
          employee_name: 'Carlos',
          started_at: '2026-09-23T12:00:00Z',
          ended_at: '2026-09-23T12:10:00Z',
          leave_reason: null,
        },
        // Buraco de 20min entre 12:10 e 12:30 — ninguém ativo, sem impedimento.
        {
          employee_id: 2,
          employee_name: 'Bruna',
          started_at: '2026-09-23T12:30:00Z',
          ended_at: '2026-09-23T12:40:00Z',
          leave_reason: null,
        },
      ],
      blocks: [],
    })
    renderModal()

    expect(await screen.findByText('Período Ocioso: 20min')).toBeInTheDocument()
    expect(screen.getByText(/possível abandono/)).toBeInTheDocument()
  })

  it('não mostra "Período Ocioso" quando as sessões cobrem a execução inteira', async () => {
    mockGetExecutionTimeline.mockResolvedValueOnce(collaborativeTimeline)
    renderModal()

    await screen.findByText('Fritar 200 empanados')
    expect(screen.queryByText(/Período Ocioso/)).not.toBeInTheDocument()
  })
})
