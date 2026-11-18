import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { DateRangePresetFilter } from '../../components/admin/DateRangePresetFilter'
import { SearchableSelect } from '../../components/SearchableSelect'
import { useDateRangeFilter } from '../../hooks/useDateRangeFilter'
import { listAuditLogs } from '../../services/auditService'
import { listStores } from '../../services/storeService'
import {
  AUDIT_ACTION_LABEL,
  AUDIT_ENTITY_TYPE_LABEL,
  entityDisplayName,
  type AuditAction,
  type AuditLog,
} from '../../types/auditLog'
import { formatDateTimeBR } from '../../utils/dateTime'
import { AuditLogDetailModal } from './AuditLogDetailModal'

const ACTOR_ALL = ''

function actorKey(entry: AuditLog): string {
  return entry.actor_type === 'USER' ? `user:${entry.actor_user_id}` : `employee:${entry.actor_employee_id}`
}

export function AuditPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'

  const dateRange = useDateRangeFilter('7dias')
  const [storeId, setStoreId] = useState('')
  const [actorFilter, setActorFilter] = useState(ACTOR_ALL)
  const [actionFilter, setActionFilter] = useState<AuditAction | ''>('')
  const [entityTypeFilter, setEntityTypeFilter] = useState('')
  const [detailEntry, setDetailEntry] = useState<AuditLog | null>(null)

  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })

  const [actorUserId, actorEmployeeId] = actorFilter
    ? (actorFilter.startsWith('user:')
        ? [Number(actorFilter.slice(5)), undefined]
        : [undefined, Number(actorFilter.slice(9))])
    : [undefined, undefined]

  const logsQuery = useQuery({
    queryKey: [
      'audit',
      dateRange.from,
      dateRange.to,
      isMaster ? storeId : undefined,
      actorUserId,
      actorEmployeeId,
      actionFilter,
      entityTypeFilter,
    ],
    queryFn: () =>
      listAuditLogs({
        dateFrom: dateRange.from,
        dateTo: dateRange.to,
        storeId: isMaster && storeId ? Number(storeId) : undefined,
        actorUserId,
        actorEmployeeId,
        action: actionFilter || undefined,
        entityType: entityTypeFilter || undefined,
      }),
    refetchInterval: 30000,
  })

  const stores = storesQuery.data ?? []
  const logs = logsQuery.data ?? []

  const actorOptions = useMemo(() => {
    const seen = new Map<string, string>()
    for (const entry of logs) {
      seen.set(actorKey(entry), entry.actor_name)
    }
    return Array.from(seen.entries())
  }, [logs])

  return (
    <div className="flex flex-col gap-6">
      <h1 className="text-xl font-semibold text-gray-900">Logs</h1>

      <div className="flex flex-col gap-3">
        <DateRangePresetFilter
          preset={dateRange.preset}
          onPresetChange={dateRange.selectPreset}
          customFrom={dateRange.customFrom}
          customTo={dateRange.customTo}
          onCustomFromChange={dateRange.setCustomFrom}
          onCustomToChange={dateRange.setCustomTo}
        />

        <div className="flex flex-wrap items-center gap-3">
          {isMaster && (
            <select
              value={storeId}
              onChange={(event) => setStoreId(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="">Todas as lojas</option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          )}

          <div className="w-64">
            <SearchableSelect
              value={actorFilter}
              onChange={setActorFilter}
              options={[
                { value: ACTOR_ALL, label: 'Todos os funcionários/usuários' },
                ...actorOptions.map(([key, name]) => ({ value: key, label: name })),
              ]}
              placeholder="Buscar funcionário/usuário…"
              emptyLabel="Nenhum encontrado."
            />
          </div>

          <select
            value={actionFilter}
            onChange={(event) => setActionFilter(event.target.value as AuditAction | '')}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="">Todas as ações</option>
            {Object.entries(AUDIT_ACTION_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>

          <select
            value={entityTypeFilter}
            onChange={(event) => setEntityTypeFilter(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="">Todas as entidades</option>
            {Object.entries(AUDIT_ENTITY_TYPE_LABEL).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Quando</th>
              <th className="px-4 py-3 font-medium">Quem</th>
              <th className="px-4 py-3 font-medium">Ação</th>
              <th className="px-4 py-3 font-medium">Entidade</th>
              {isMaster && <th className="px-4 py-3 font-medium">Loja</th>}
              <th className="px-4 py-3 font-medium">Detalhes</th>
            </tr>
          </thead>
          <tbody>
            {logsQuery.isLoading && (
              <tr>
                <td colSpan={isMaster ? 6 : 5} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!logsQuery.isLoading && logs.length === 0 && (
              <tr>
                <td colSpan={isMaster ? 6 : 5} className="px-4 py-6 text-center text-gray-500">
                  Nenhuma ação registrada neste período.
                </td>
              </tr>
            )}
            {logs.map((entry) => (
              <tr key={entry.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 text-gray-600">{formatDateTimeBR(entry.created_at)}</td>
                <td className="px-4 py-3 text-gray-900">
                  {entry.actor_name}
                  <span className="ml-1.5 rounded-full bg-gray-100 px-2 py-0.5 text-xs font-medium text-gray-500">
                    {entry.actor_type === 'USER' ? 'Usuário' : 'Funcionário'}
                  </span>
                </td>
                <td className="px-4 py-3 text-gray-600">{AUDIT_ACTION_LABEL[entry.action] ?? entry.action}</td>
                <td className="px-4 py-3 text-gray-600">
                  {AUDIT_ENTITY_TYPE_LABEL[entry.entity_type] ?? entry.entity_type}
                  {(() => {
                    const name = entityDisplayName(entry)
                    return name ? ` (${name})` : ` #${entry.entity_id}`
                  })()}
                </td>
                {isMaster && <td className="px-4 py-3 text-gray-600">{entry.store_name ?? '—'}</td>}
                <td className="px-4 py-3">
                  <button
                    type="button"
                    onClick={() => setDetailEntry(entry)}
                    className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                  >
                    Ver detalhes
                  </button>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {detailEntry && <AuditLogDetailModal entry={detailEntry} onClose={() => setDetailEntry(null)} />}
    </div>
  )
}
