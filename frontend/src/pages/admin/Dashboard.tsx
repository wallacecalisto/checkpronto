import { useState, type ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts'
import { useAuth } from '../../auth/useAuth'
import { DateRangePresetFilter } from '../../components/admin/DateRangePresetFilter'
import { useSelectedStore } from '../../contexts/SelectedStoreContext'
import { useDateRangeFilter } from '../../hooks/useDateRangeFilter'
import { LivePanel } from '../operational/LivePanel'
import {
  getActivityFeed,
  getDashboardExceptions,
  getDashboardRanking,
  getDashboardSummary,
  getDashboardWeeklyTrend,
  getRecentChecklists,
} from '../../services/dashboardService'
import { listSectors } from '../../services/sectorService'
import { listStores } from '../../services/storeService'
import { listTaskAssignments } from '../../services/taskAssignmentService'
import { SHIFT_LABEL } from '../../types/checklistExecution'
import type { ActivityFeedEntry, ExceptionEntry, RecentChecklistEntry } from '../../types/dashboard'
import { DAY_OF_WEEK_SHORT_LABEL } from '../../types/taskAssignment'
import { formatDateTimeBR, formatDurationShort, formatTimeBR } from '../../utils/dateTime'
import { DashboardListModal } from './DashboardListModal'
import { EmployeeListModal } from './EmployeeListModal'
import { EmployeeProfileModal } from './EmployeeProfileModal'

const EXCEPTION_CARD_CLASS: Record<ExceptionEntry['type'], string> = {
  TAREFA: 'border-red-200 bg-red-50',
  CHECKLIST: 'border-purple-200 bg-purple-50',
  IMPEDIMENTO: 'border-amber-200 bg-amber-50',
}

const EXCEPTION_BADGE_CLASS: Record<ExceptionEntry['type'], string> = {
  TAREFA: 'bg-red-100 text-red-700',
  CHECKLIST: 'bg-purple-100 text-purple-700',
  IMPEDIMENTO: 'bg-amber-100 text-amber-700',
}

const EXCEPTION_TYPE_LABEL: Record<ExceptionEntry['type'], string> = {
  TAREFA: 'Tarefa',
  CHECKLIST: 'Checklist',
  IMPEDIMENTO: 'Impedimento',
}

function ExceptionRow({ entry }: { entry: ExceptionEntry }) {
  return (
    <div className={`rounded-xl border p-3 text-sm ${EXCEPTION_CARD_CLASS[entry.type]}`}>
      <div className="flex items-center justify-between gap-2">
        <p className="font-medium text-gray-900">
          {entry.title} <span className="font-normal text-gray-500">— {entry.user_name}</span>
        </p>
        <span className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-semibold ${EXCEPTION_BADGE_CLASS[entry.type]}`}>
          {EXCEPTION_TYPE_LABEL[entry.type]}
        </span>
      </div>
      <p className="mt-1 text-xs text-gray-500">{formatDateTimeBR(entry.date)}</p>
      {entry.reason && <p className="mt-2 text-sm text-gray-700">"{entry.reason}"</p>}
    </div>
  )
}

function ActivityFeedRow({ entry }: { entry: ActivityFeedEntry }) {
  return (
    <div className="flex items-center gap-3 border-b border-gray-100 pb-2 last:border-0">
      <span className="w-12 shrink-0 text-xs text-gray-400">{formatTimeBR(entry.occurred_at)}</span>
      <p className="text-sm text-gray-700">
        <span className="font-medium text-gray-900">{entry.actor_name}</span> {entry.description}
      </p>
    </div>
  )
}

function RecentChecklistRow({ entry }: { entry: RecentChecklistEntry }) {
  return (
    <div className="border-b border-gray-100 pb-2 last:border-0">
      <div className="flex items-center justify-between gap-2">
        <p className="text-sm font-medium text-gray-900">
          {entry.template_name} <span className="font-normal text-gray-500">— {SHIFT_LABEL[entry.shift]}</span>
        </p>
        <span
          className={`shrink-0 rounded-full px-2 py-0.5 text-xs font-medium ${
            entry.status !== 'COMPLETED'
              ? 'bg-emerald-50 text-emerald-600'
              : entry.fully_validated
                ? 'bg-emerald-50 text-emerald-600'
                : 'bg-orange-50 text-orange-600'
          }`}
        >
          {entry.status !== 'COMPLETED' ? 'Em andamento' : entry.fully_validated ? 'Validado' : 'Pendente'}
        </span>
      </div>
      <p className="mt-1 text-xs text-gray-500">
        Executado por <span className="font-medium text-gray-700">{entry.executed_by_name}</span>
        {entry.validated_by_names.length > 0 && (
          <>
            {' '}
            — Validado por <span className="font-medium text-gray-700">{entry.validated_by_names.join(', ')}</span>
          </>
        )}
      </p>
    </div>
  )
}

interface KpiCardProps {
  label: string
  value: ReactNode
  tone?: 'default' | 'warning'
}

function KpiCard({ label, value, tone = 'default' }: KpiCardProps) {
  return (
    <div className="animate-fade-in-up rounded-2xl border border-gray-100/50 bg-white p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
      <p className="text-sm text-gray-500">{label}</p>
      <p className={`mt-2 text-3xl font-bold ${tone === 'warning' ? 'text-orange-500' : 'text-gray-900'}`}>{value}</p>
    </div>
  )
}

const MEDAL = ['🥇', '🥈', '🥉']
const RANKING_PREVIEW_LIMIT = 5

export function AdminDashboardPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'

  const dateRange = useDateRangeFilter('7dias')
  const { storeId, setStoreId } = useSelectedStore()
  const [isEmployeeListOpen, setIsEmployeeListOpen] = useState(false)
  const [selectedEmployee, setSelectedEmployee] = useState<{ id: number; name: string } | null>(null)
  const [rankingSectorId, setRankingSectorId] = useState('')
  const [openListModal, setOpenListModal] = useState<'feed' | 'checklists' | 'exceptions' | null>(null)

  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })
  const effectiveStoreId = isMaster && storeId !== null ? storeId : undefined
  const sectorsQuery = useQuery({
    queryKey: ['sectors', 'for-dashboard-ranking', effectiveStoreId],
    queryFn: () => listSectors({ activeOnly: true, storeId: effectiveStoreId }),
  })
  const sectors = sectorsQuery.data ?? []

  const filterParams = { startDate: dateRange.from, endDate: dateRange.to, storeId: effectiveStoreId }
  const filterKey = [dateRange.from, dateRange.to, effectiveStoreId]

  const summaryQuery = useQuery({
    queryKey: ['dashboard', 'summary', ...filterKey],
    queryFn: () => getDashboardSummary(filterParams),
  })
  const rankingQuery = useQuery({
    queryKey: ['dashboard', 'ranking', ...filterKey, RANKING_PREVIEW_LIMIT, rankingSectorId],
    queryFn: () =>
      getDashboardRanking({
        ...filterParams,
        limit: RANKING_PREVIEW_LIMIT,
        sectorId: rankingSectorId ? Number(rankingSectorId) : undefined,
      }),
  })
  const trendQuery = useQuery({
    queryKey: ['dashboard', 'weekly-trend', ...filterKey],
    queryFn: () => getDashboardWeeklyTrend(filterParams),
  })
  const feedQuery = useQuery({
    queryKey: ['dashboard', 'activity-feed', effectiveStoreId],
    queryFn: () => getActivityFeed({ storeId: effectiveStoreId }),
    refetchInterval: 30000,
  })
  const exceptionsQuery = useQuery({
    queryKey: ['dashboard', 'exceptions', ...filterKey],
    queryFn: () => getDashboardExceptions(filterParams),
  })
  const recentChecklistsQuery = useQuery({
    queryKey: ['dashboard', 'recent-checklists', effectiveStoreId],
    queryFn: () => getRecentChecklists({ storeId: effectiveStoreId }),
    refetchInterval: 30000,
  })

  const inProgressQuery = useQuery({
    queryKey: ['dashboard', 'in-progress', effectiveStoreId],
    queryFn: () => listTaskAssignments({ status: 'IN_PROGRESS', storeId: effectiveStoreId }),
    refetchInterval: 5000,
  })
  const stores = storesQuery.data ?? []
  const summary = summaryQuery.data
  const ranking = rankingQuery.data ?? []
  const trend = trendQuery.data ?? []
  const feed = feedQuery.data ?? []
  const inProgressAssignments = inProgressQuery.data ?? []
  const pendingTasks = summary?.pending_tasks ?? 0
  const exceptions = exceptionsQuery.data ?? []
  const recentChecklists = recentChecklistsQuery.data ?? []

  const chartData = trend.map((point) => ({
    day: DAY_OF_WEEK_SHORT_LABEL[point.day_of_week],
    minutos: point.avg_execution_seconds !== null ? Math.round((point.avg_execution_seconds / 60) * 10) / 10 : null,
    concluidas: point.completed_count,
  }))

  return (
    <div className="flex flex-col gap-6">
      <div>
        <h1 className="text-xl font-semibold text-gray-900">Painel</h1>
        <p className="mt-1 text-sm text-gray-500">Olá, {user?.name} — visão geral de desempenho da operação.</p>
      </div>

      <div className="flex flex-col gap-3">
        <DateRangePresetFilter
          preset={dateRange.preset}
          onPresetChange={dateRange.selectPreset}
          customFrom={dateRange.customFrom}
          customTo={dateRange.customTo}
          onCustomFromChange={dateRange.setCustomFrom}
          onCustomToChange={dateRange.setCustomTo}
        />

        {isMaster && (
          <select
            aria-label="Loja"
            value={storeId !== null ? String(storeId) : ''}
            onChange={(event) => setStoreId(event.target.value ? Number(event.target.value) : null)}
            className="w-fit rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="">Todas as lojas</option>
            {stores.map((store) => (
              <option key={store.id} value={store.id}>
                {store.name}
              </option>
            ))}
          </select>
        )}
      </div>

      <div className="grid gap-4 sm:grid-cols-2 lg:grid-cols-4">
        <KpiCard label="Taxa de Conclusão" value={`${(summary?.completion_rate ?? 0).toFixed(0)}%`} />
        <KpiCard label="Tarefas Concluídas" value={summary?.completed_tasks ?? 0} />
        <KpiCard label="Tarefas Pendentes (agora)" value={pendingTasks} />
        <KpiCard
          label="Checklists Divergentes"
          value={summary?.checklist_divergent_count ?? 0}
          tone={(summary?.checklist_divergent_count ?? 0) > 0 ? 'warning' : 'default'}
        />
      </div>

      <div className="animate-fade-in-up rounded-2xl border-2 border-emerald-100 bg-emerald-50/40 p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <div className="flex items-center gap-2">
          <span className="h-2 w-2 animate-pulse rounded-full bg-emerald-500" />
          <h2 className="font-semibold text-gray-900">Operação em Andamento</h2>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Tarefas em execução agora, com cronômetro ao vivo — laranja quando o tempo estimado estoura.
        </p>
        <div className="mt-4">
          {inProgressQuery.isLoading ? (
            <p className="text-sm text-gray-400">Carregando…</p>
          ) : (
            <LivePanel assignments={inProgressAssignments} />
          )}
        </div>
      </div>

      <div className="grid gap-4 lg:grid-cols-3">
        <div className="animate-fade-in-up rounded-2xl border border-gray-100/50 bg-white p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md lg:col-span-2">
          <h2 className="font-semibold text-gray-900">Tempo médio de conclusão por dia da semana</h2>
          <p className="mt-1 text-xs text-gray-400">
            Tarefas rotineiras têm volume parecido todo dia — o que importa é comparar a velocidade (ex.: fim de semana
            mais lento que os dias úteis?).
          </p>
          <div className="mt-4 h-72">
            {trendQuery.isLoading ? (
              <div className="flex h-full items-center justify-center text-sm text-gray-400">Carregando…</div>
            ) : (
              <ResponsiveContainer width="100%" height="100%">
                <BarChart data={chartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="#e5e7eb" vertical={false} />
                  <XAxis dataKey="day" tick={{ fontSize: 12, fill: '#6b7280' }} axisLine={false} tickLine={false} />
                  <YAxis
                    tick={{ fontSize: 12, fill: '#6b7280' }}
                    axisLine={false}
                    tickLine={false}
                    unit="min"
                  />
                  <Tooltip
                    cursor={{ fill: '#f3f4f6' }}
                    formatter={(value, _name, item) => [
                      value === null ? 'Sem conclusões' : `${value} min`,
                      `Tempo médio (${item.payload.concluidas} concluída(s))`,
                    ]}
                  />
                  <Bar dataKey="minutos" name="Tempo médio" fill="#6366f1" radius={[4, 4, 0, 0]} />
                </BarChart>
              </ResponsiveContainer>
            )}
          </div>
        </div>

        <div className="animate-fade-in-up rounded-2xl border border-gray-100/50 bg-white p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Top 5 Funcionários</h2>
            <button
              type="button"
              onClick={() => setIsEmployeeListOpen(true)}
              className="text-xs font-medium text-emerald-600 hover:underline"
            >
              Ver todos
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-400">Por velocidade de execução — clique para ver o perfil.</p>

          <select
            aria-label="Setor (ranking)"
            value={rankingSectorId}
            onChange={(event) => setRankingSectorId(event.target.value)}
            className="mt-2 w-full rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-xs text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            <option value="">Loja inteira</option>
            {sectors.map((sector) => (
              <option key={sector.id} value={sector.id}>
                {sector.name}
              </option>
            ))}
          </select>

          {rankingQuery.isLoading ? (
            <p className="mt-4 text-sm text-gray-400">Carregando…</p>
          ) : ranking.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">Nenhuma atividade registrada neste período.</p>
          ) : (
            <ol className="mt-4 flex max-h-96 flex-col gap-3 overflow-y-auto">
              {ranking.map((entry, index) => (
                <li key={entry.employee_id}>
                  <button
                    type="button"
                    onClick={() => setSelectedEmployee({ id: entry.employee_id, name: entry.employee_name })}
                    className="flex w-full items-center gap-3 rounded-xl p-1.5 text-left transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-gray-50 hover:shadow-md"
                  >
                    <span className="w-6 shrink-0 text-center text-lg">{MEDAL[index] ?? index + 1}</span>
                    <div className="min-w-0 flex-1">
                      <p className="truncate text-sm font-medium text-gray-900">{entry.employee_name}</p>
                      <p className="text-xs text-gray-500">
                        {entry.completed_count} concluída(s)
                        {entry.avg_execution_seconds !== null && (
                          <> — {formatDurationShort(entry.avg_execution_seconds)} em média</>
                        )}
                      </p>
                    </div>
                    <span
                      className={`shrink-0 rounded-full px-2.5 py-1 text-xs font-semibold ${
                        entry.on_time_rate !== null ? 'bg-emerald-50 text-emerald-600' : 'bg-gray-100 text-gray-500'
                      }`}
                    >
                      {entry.on_time_rate !== null ? `${entry.on_time_rate.toFixed(0)}% no prazo` : `${entry.completed_count}`}
                    </span>
                  </button>
                </li>
              ))}
            </ol>
          )}
        </div>
      </div>

      <div className="animate-fade-in-up rounded-2xl border-2 border-red-100 bg-red-50/40 p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <div className="flex items-center justify-between">
          <h2 className="font-semibold text-gray-900">Alertas e Exceções</h2>
          <button
            type="button"
            onClick={() => setOpenListModal('exceptions')}
            className="text-xs font-medium text-emerald-600 hover:underline"
          >
            Ver todos
          </button>
        </div>
        <p className="mt-1 text-xs text-gray-500">
          Tarefas não realizadas ou com observação, e itens de checklist marcados como divergentes na validação —
          período filtrado.
        </p>

        {exceptionsQuery.isLoading ? (
          <p className="mt-4 text-sm text-gray-400">Carregando…</p>
        ) : exceptions.length === 0 ? (
          <p className="mt-4 text-sm text-gray-400">Nenhuma exceção registrada neste período. 🎉</p>
        ) : (
          <ul className="mt-4 flex max-h-80 flex-col gap-2 overflow-y-auto">
            {exceptions.map((entry) => (
              <li key={entry.id}>
                <ExceptionRow entry={entry} />
              </li>
            ))}
          </ul>
        )}
      </div>

      <div className="grid gap-4 lg:grid-cols-2">
        <div className="animate-fade-in-up rounded-2xl border border-gray-100/50 bg-white p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Radar Ao Vivo</h2>
            <button
              type="button"
              onClick={() => setOpenListModal('feed')}
              className="text-xs font-medium text-emerald-600 hover:underline"
            >
              Ver todos
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-400">Últimas ações operacionais de hoje.</p>

          {feedQuery.isLoading ? (
            <p className="mt-4 text-sm text-gray-400">Carregando…</p>
          ) : feed.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">Nenhuma ação registrada hoje ainda.</p>
          ) : (
            <ul className="mt-4 flex max-h-64 flex-col gap-2 overflow-y-auto">
              {feed.map((entry) => (
                <li key={entry.id}>
                  <ActivityFeedRow entry={entry} />
                </li>
              ))}
            </ul>
          )}
        </div>

        <div className="animate-fade-in-up rounded-2xl border border-gray-100/50 bg-white p-5 shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
          <div className="flex items-center justify-between">
            <h2 className="font-semibold text-gray-900">Últimos Checklists</h2>
            <button
              type="button"
              onClick={() => setOpenListModal('checklists')}
              className="text-xs font-medium text-emerald-600 hover:underline"
            >
              Ver todos
            </button>
          </div>
          <p className="mt-1 text-xs text-gray-400">Os mais recentes, com quem executou e quem validou.</p>

          {recentChecklistsQuery.isLoading ? (
            <p className="mt-4 text-sm text-gray-400">Carregando…</p>
          ) : recentChecklists.length === 0 ? (
            <p className="mt-4 text-sm text-gray-400">Nenhum checklist registrado ainda.</p>
          ) : (
            <ul className="mt-4 flex max-h-64 flex-col gap-2 overflow-y-auto">
              {recentChecklists.map((entry) => (
                <li key={entry.id}>
                  <RecentChecklistRow entry={entry} />
                </li>
              ))}
            </ul>
          )}
        </div>
      </div>

      {isEmployeeListOpen && (
        <EmployeeListModal
          storeId={effectiveStoreId}
          onSelectEmployee={(employee) => {
            setIsEmployeeListOpen(false)
            setSelectedEmployee(employee)
          }}
          onClose={() => setIsEmployeeListOpen(false)}
        />
      )}

      {selectedEmployee && (
        <EmployeeProfileModal
          employeeId={selectedEmployee.id}
          employeeName={selectedEmployee.name}
          startDate={dateRange.from}
          endDate={dateRange.to}
          onClose={() => setSelectedEmployee(null)}
        />
      )}

      {openListModal === 'feed' && (
        <DashboardListModal<ActivityFeedEntry>
          title="Radar Ao Vivo — todas as ações"
          description="Todas as ações operacionais do período selecionado (o card resumido no Painel mostra só as de hoje)."
          queryKey="activity-feed"
          fetchRows={(params) =>
            getActivityFeed({ storeId: effectiveStoreId, startDate: params.startDate, endDate: params.endDate, limit: 100 })
          }
          renderRow={(entry) => <ActivityFeedRow entry={entry} />}
          rowKey={(entry) => entry.id}
          emptyLabel="Nenhuma ação registrada neste período."
          onClose={() => setOpenListModal(null)}
        />
      )}

      {openListModal === 'checklists' && (
        <DashboardListModal<RecentChecklistEntry>
          title="Últimos Checklists — todos"
          description="Checklists do período selecionado (o card resumido no Painel mostra só os mais recentes)."
          queryKey="recent-checklists"
          fetchRows={(params) =>
            getRecentChecklists({
              storeId: effectiveStoreId,
              startDate: params.startDate,
              endDate: params.endDate,
              limit: 200,
            })
          }
          renderRow={(entry) => <RecentChecklistRow entry={entry} />}
          rowKey={(entry) => entry.id}
          emptyLabel="Nenhum checklist registrado neste período."
          onClose={() => setOpenListModal(null)}
        />
      )}

      {openListModal === 'exceptions' && (
        <DashboardListModal<ExceptionEntry>
          title="Alertas e Exceções — todos"
          description="Todas as exceções do período selecionado."
          queryKey="exceptions"
          fetchRows={(params) =>
            getDashboardExceptions({
              storeId: effectiveStoreId,
              startDate: params.startDate,
              endDate: params.endDate,
              limit: 200,
            })
          }
          renderRow={(entry) => <ExceptionRow entry={entry} />}
          rowKey={(entry) => entry.id}
          emptyLabel="Nenhuma exceção registrada neste período."
          onClose={() => setOpenListModal(null)}
        />
      )}
    </div>
  )
}
