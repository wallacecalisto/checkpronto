import { Modal } from '../../components/Modal'
import {
  AUDIT_ACTION_LABEL,
  AUDIT_ENTITY_TYPE_LABEL,
  auditFieldLabel,
  auditValueLabel,
  entityDisplayName,
  type AuditLog,
} from '../../types/auditLog'
import { formatDateTimeBR } from '../../utils/dateTime'

interface AuditLogDetailModalProps {
  entry: AuditLog
  onClose: () => void
}

function formatValue(key: string, value: unknown): string {
  if (value === null || value === undefined) return '—'
  if (typeof value === 'boolean') return value ? 'Sim' : 'Não'
  const translated = auditValueLabel(key, value)
  if (translated) return translated
  if (Array.isArray(value)) return JSON.stringify(value, null, 2)
  if (typeof value === 'object') return JSON.stringify(value, null, 2)
  return String(value)
}

function DiffTable({ before, after }: { before: Record<string, unknown> | null; after: Record<string, unknown> | null }) {
  const keys = Array.from(new Set([...Object.keys(before ?? {}), ...Object.keys(after ?? {})]))

  if (keys.length === 0) {
    return <p className="text-sm text-gray-500">Sem dados adicionais para esta ação.</p>
  }

  return (
    <table className="w-full text-left text-sm">
      <thead className="border-b border-gray-200 text-gray-500">
        <tr>
          <th className="px-3 py-2 font-medium">Campo</th>
          <th className="px-3 py-2 font-medium">Antes</th>
          <th className="px-3 py-2 font-medium">Depois</th>
        </tr>
      </thead>
      <tbody>
        {keys.map((key) => {
          const beforeValue = before ? before[key] : undefined
          const afterValue = after ? after[key] : undefined
          const changed = before !== null && after !== null && JSON.stringify(beforeValue) !== JSON.stringify(afterValue)

          return (
            <tr key={key} className={`border-b border-gray-100 last:border-0 ${changed ? 'bg-amber-50' : ''}`}>
              <td className="px-3 py-2 font-medium text-gray-700">{auditFieldLabel(key)}</td>
              <td className="whitespace-pre-wrap px-3 py-2 text-gray-600">{before ? formatValue(key, beforeValue) : '—'}</td>
              <td className="whitespace-pre-wrap px-3 py-2 text-gray-900">{after ? formatValue(key, afterValue) : '—'}</td>
            </tr>
          )
        })}
      </tbody>
    </table>
  )
}

export function AuditLogDetailModal({ entry, onClose }: AuditLogDetailModalProps) {
  return (
    <Modal title="Detalhes da ação" onClose={onClose}>
      <div className="flex flex-col gap-4">
        <dl className="grid grid-cols-2 gap-x-4 gap-y-2 text-sm">
          <dt className="text-gray-500">Ação</dt>
          <dd className="text-gray-900">{AUDIT_ACTION_LABEL[entry.action] ?? entry.action}</dd>
          <dt className="text-gray-500">Entidade</dt>
          <dd className="text-gray-900">
            {AUDIT_ENTITY_TYPE_LABEL[entry.entity_type] ?? entry.entity_type}
            {(() => {
              const name = entityDisplayName(entry)
              return name ? ` (${name})` : ` #${entry.entity_id}`
            })()}
          </dd>
          <dt className="text-gray-500">Quem fez</dt>
          <dd className="text-gray-900">{entry.actor_name}</dd>
          <dt className="text-gray-500">Quando</dt>
          <dd className="text-gray-900">{formatDateTimeBR(entry.created_at)}</dd>
          {entry.store_name && (
            <>
              <dt className="text-gray-500">Loja</dt>
              <dd className="text-gray-900">{entry.store_name}</dd>
            </>
          )}
        </dl>

        <div className="overflow-x-auto rounded-lg border border-gray-200">
          <DiffTable before={entry.before_data} after={entry.after_data} />
        </div>

        <div className="flex justify-end">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
          >
            Fechar
          </button>
        </div>
      </div>
    </Modal>
  )
}
