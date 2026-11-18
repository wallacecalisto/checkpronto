import type { ReactNode } from 'react'

interface KanbanColumnProps {
  title: string
  count: number
  emptyLabel: string
  children: ReactNode
}

export function KanbanColumn({ title, count, emptyLabel, children }: KanbanColumnProps) {
  return (
    <div className="flex flex-col gap-3 rounded-2xl border border-slate-100 bg-slate-50 p-3">
      <div className="flex items-center justify-between px-1">
        <h3 className="text-sm font-semibold text-slate-700">{title}</h3>
        <span className="rounded-full bg-white px-2 py-0.5 text-xs font-medium text-slate-500 shadow-sm">{count}</span>
      </div>
      <div className="flex max-h-[65vh] flex-col gap-3 overflow-y-auto">
        {count === 0 ? <p className="py-4 text-center text-sm text-slate-400">{emptyLabel}</p> : children}
      </div>
    </div>
  )
}
