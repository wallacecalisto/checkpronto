import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import type { TaskAssignment } from '../../types/taskAssignment'
import { LivePanel } from './LivePanel'

const assignment: TaskAssignment = {
  id: 1,
  task_id: 1,
  store_id: 1,
  day_of_week: 'MONDAY',
  task_title: 'Fritar 200 empanados',
  task_description: null,
  estimated_duration_minutes: 10,
  requires_photo_proof: false,
  shift: 'Manhã',
  sector_id: 1,
  sector_name: 'Cozinha',
  status: 'IN_PROGRESS',
  started_at: '2026-01-01T12:00:00Z',
  completed_at: null,
  started_by_employee_id: 1,
  completed_by_employee_id: null,
  started_by_user_id: null,
  completed_by_user_id: null,
  result: null,
  justification: null,
  observation: null,
  photo_url: null,
  extra_photo_urls: [],
  elapsed_seconds: 300,
  active_participants: [{ employee_id: 1, employee_name: 'Carlos', started_at: '2026-01-01T12:00:00Z' }],
  blocked_at: null,
  block_reason: null,
  blocked_by_employee_id: null,
  latest_execution_history_id: null,
}

describe('LivePanel', () => {
  it('mostra o cronômetro e a barra de SLA por padrão', () => {
    render(<LivePanel assignments={[assignment]} />)

    expect(screen.getByText(/fazendo/)).toBeInTheDocument()
    expect(screen.getByText('05:00 / 10:00')).toBeInTheDocument()
  })

  it('esconde o tempo, mas mantém "quem está fazendo o quê"', () => {
    render(<LivePanel assignments={[assignment]} hideTimer />)

    expect(screen.getByText(/fazendo/)).toBeInTheDocument()
    expect(screen.queryByText('05:00 / 10:00')).not.toBeInTheDocument()
  })

  it('mostra quem está ATIVO agora, não quem só iniciou a tarefa', () => {
    const collaborative: TaskAssignment = {
      ...assignment,
      active_participants: [{ employee_id: 2, employee_name: 'Bruna', started_at: '2026-01-01T12:10:00Z' }],
    }
    render(<LivePanel assignments={[collaborative]} />)

    expect(screen.getByText(/Bruna/)).toBeInTheDocument()
    expect(screen.queryByText(/Carlos/)).not.toBeInTheDocument()
  })

  it('mostra "Ninguém no momento" quando todo mundo saiu (nenhuma sessão aberta)', () => {
    const noOneActive: TaskAssignment = { ...assignment, active_participants: [] }
    render(<LivePanel assignments={[noOneActive]} />)

    expect(screen.getByText(/ninguém no momento/i)).toBeInTheDocument()
  })

  it('lista todos os participantes ativos quando mais de um está na tarefa', () => {
    const collaborative: TaskAssignment = {
      ...assignment,
      active_participants: [
        { employee_id: 1, employee_name: 'Carlos', started_at: '2026-01-01T12:00:00Z' },
        { employee_id: 2, employee_name: 'Bruna', started_at: '2026-01-01T12:10:00Z' },
      ],
    }
    render(<LivePanel assignments={[collaborative]} />)

    expect(screen.getByText(/Carlos, Bruna/)).toBeInTheDocument()
  })
})
