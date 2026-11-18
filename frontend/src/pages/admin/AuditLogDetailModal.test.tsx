import { render, screen } from '@testing-library/react'
import { describe, expect, it, vi } from 'vitest'
import type { AuditLog } from '../../types/auditLog'
import { AuditLogDetailModal } from './AuditLogDetailModal'

function buildEntry(overrides: Partial<AuditLog> = {}): AuditLog {
  return {
    id: 1,
    store_id: 1,
    store_name: 'Loja Teste',
    actor_type: 'USER',
    actor_user_id: 1,
    actor_employee_id: null,
    actor_name: 'Gestora',
    action: 'CREATE',
    entity_type: 'TASK_ASSIGNMENT',
    entity_id: 10,
    before_data: null,
    after_data: null,
    created_at: '2026-09-13T12:00:00Z',
    ...overrides,
  }
}

describe('AuditLogDetailModal', () => {
  it('traduz o valor de day_of_week (SUNDAY -> Domingo)', async () => {
    const entry = buildEntry({ after_data: { day_of_week: 'SUNDAY' } })
    render(<AuditLogDetailModal entry={entry} onClose={vi.fn()} />)

    expect(await screen.findByText('Domingo')).toBeInTheDocument()
    expect(screen.queryByText('SUNDAY')).not.toBeInTheDocument()
  })

  it('traduz o valor de status (IN_PROGRESS -> Em andamento)', async () => {
    const entry = buildEntry({ before_data: { status: 'PENDING' }, after_data: { status: 'IN_PROGRESS' } })
    render(<AuditLogDetailModal entry={entry} onClose={vi.fn()} />)

    expect(await screen.findByText('Pendente')).toBeInTheDocument()
    expect(screen.getByText('Em andamento')).toBeInTheDocument()
  })

  it('não mexe em valores de campos sem tradução configurada', async () => {
    const entry = buildEntry({ after_data: { name: 'Tarefa Nova' } })
    render(<AuditLogDetailModal entry={entry} onClose={vi.fn()} />)

    expect(await screen.findByText('Tarefa Nova')).toBeInTheDocument()
  })
})
