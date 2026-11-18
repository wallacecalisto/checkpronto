import type { ReactNode } from 'react'
import { useQuery } from '@tanstack/react-query'
import { DateRangePresetFilter } from '../../components/admin/DateRangePresetFilter'
import { Modal } from '../../components/Modal'
import { useDateRangeFilter } from '../../hooks/useDateRangeFilter'

interface DashboardListModalProps<T> {
  title: string
  description?: string
  onClose: () => void
  queryKey: string
  fetchRows: (params: { startDate: string; endDate: string }) => Promise<T[]>
  renderRow: (row: T) => ReactNode
  rowKey: (row: T) => string | number
  emptyLabel: string
}

export function DashboardListModal<T>({
  title,
  description,
  onClose,
  queryKey,
  fetchRows,
  renderRow,
  rowKey,
  emptyLabel,
}: DashboardListModalProps<T>) {
  const dateRange = useDateRangeFilter('7dias')

  const rowsQuery = useQuery({
    queryKey: ['dashboard-list-modal', queryKey, dateRange.from, dateRange.to],
    queryFn: () => fetchRows({ startDate: dateRange.from, endDate: dateRange.to }),
  })
  const rows = rowsQuery.data ?? []

  return (
    <Modal title={title} onClose={onClose}>
      <div className="flex flex-col gap-4">
        {description && <p className="text-sm text-gray-500">{description}</p>}

        <DateRangePresetFilter
          preset={dateRange.preset}
          onPresetChange={dateRange.selectPreset}
          customFrom={dateRange.customFrom}
          customTo={dateRange.customTo}
          onCustomFromChange={dateRange.setCustomFrom}
          onCustomToChange={dateRange.setCustomTo}
        />

        {rowsQuery.isLoading ? (
          <p className="text-sm text-gray-400">Carregando…</p>
        ) : rows.length === 0 ? (
          <p className="text-sm text-gray-400">{emptyLabel}</p>
        ) : (
          <ul className="flex max-h-[55vh] flex-col gap-2 overflow-y-auto">
            {rows.map((row) => (
              <li key={rowKey(row)}>{renderRow(row)}</li>
            ))}
          </ul>
        )}
      </div>
    </Modal>
  )
}
