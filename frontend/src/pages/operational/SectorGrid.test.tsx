import { render, screen } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { describe, expect, it, vi } from 'vitest'
import type { Sector } from '../../types/sector'
import type { TaskAssignment } from '../../types/taskAssignment'
import { SectorGrid } from './SectorGrid'

const cozinha: Sector = { id: 1, store_id: 1, name: 'Cozinha Quente', active: true }
const sushi: Sector = { id: 2, store_id: 1, name: 'Sushi', active: true }

function makeAssignment(overrides: Partial<TaskAssignment>): TaskAssignment {
  return {
    id: 1,
    task_id: 1,
    store_id: 1,
    day_of_week: 'MONDAY',
    task_title: 'Tarefa',
    task_description: null,
    estimated_duration_minutes: null,
    requires_photo_proof: false,
    shift: 'Manhã',
    sector_id: cozinha.id,
    sector_name: cozinha.name,
    status: 'PENDING',
    started_at: null,
    completed_at: null,
    started_by_employee_id: null,
    completed_by_employee_id: null,
    started_by_user_id: null,
    completed_by_user_id: null,
    result: null,
    justification: null,
    observation: null,
    photo_url: null,
    extra_photo_urls: [],
    elapsed_seconds: null,
    active_participants: [],
    blocked_at: null,
    block_reason: null,
    blocked_by_employee_id: null,
    latest_execution_history_id: null,
    ...overrides,
  }
}

describe('SectorGrid', () => {
  it('lista os setores e chama onSelect ao tocar num deles', async () => {
    const onSelect = vi.fn()
    const user = userEvent.setup()
    render(<SectorGrid sectors={[cozinha, sushi]} assignments={[]} onSelect={onSelect} />)

    expect(screen.getByText('Cozinha Quente')).toBeInTheDocument()
    expect(screen.getByText('Sushi')).toBeInTheDocument()

    await user.click(screen.getByText('Sushi'))

    expect(onSelect).toHaveBeenCalledWith(sushi)
  })

  it('mostra a contagem de tarefas em andamento e impedidas por setor', () => {
    const assignments = [
      makeAssignment({ id: 1, sector_id: cozinha.id, status: 'IN_PROGRESS' }),
      makeAssignment({ id: 2, sector_id: cozinha.id, status: 'IN_PROGRESS' }),
      makeAssignment({ id: 3, sector_id: cozinha.id, status: 'BLOCKED' }),
      makeAssignment({ id: 4, sector_id: sushi.id, status: 'PENDING' }),
    ]
    render(<SectorGrid sectors={[cozinha, sushi]} assignments={assignments} onSelect={vi.fn()} />)

    expect(screen.getByText('2 em andamento')).toBeInTheDocument()
    expect(screen.getByText('1 impedida')).toBeInTheDocument()
  })

  it('mostra mensagem quando não há setores cadastrados', () => {
    render(<SectorGrid sectors={[]} assignments={[]} onSelect={vi.fn()} />)

    expect(screen.getByText('Nenhum setor cadastrado nesta loja.')).toBeInTheDocument()
  })
})
