import type { Sector } from '../../types/sector'
import type { TaskAssignment } from '../../types/taskAssignment'

interface SectorGridProps {
  sectors: Sector[]
  // Usado só para o contador "X em andamento" de cada card — não filtra a
  // lista de setores em si.
  assignments: TaskAssignment[]
  onSelect: (sector: Sector) => void
}

export function SectorGrid({ sectors, assignments, onSelect }: SectorGridProps) {
  if (sectors.length === 0) {
    return <p className="text-center text-slate-500">Nenhum setor cadastrado nesta loja.</p>
  }

  return (
    <div className="grid grid-cols-2 gap-5 sm:grid-cols-3">
      {sectors.map((sector) => {
        const inProgressCount = assignments.filter(
          (assignment) => assignment.sector_id === sector.id && assignment.status === 'IN_PROGRESS',
        ).length
        const blockedCount = assignments.filter(
          (assignment) => assignment.sector_id === sector.id && assignment.status === 'BLOCKED',
        ).length

        return (
          <button
            key={sector.id}
            type="button"
            onClick={() => onSelect(sector)}
            className="flex flex-col items-center justify-center gap-2 rounded-2xl border border-slate-200 bg-white px-4 py-8 text-center shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md active:scale-95"
          >
            <span className="text-lg font-semibold text-slate-800">{sector.name}</span>
            <div className="flex flex-wrap items-center justify-center gap-1.5">
              {inProgressCount > 0 && (
                <span className="rounded-full bg-indigo-50 px-2.5 py-1 text-xs font-medium text-indigo-600">
                  {inProgressCount} em andamento
                </span>
              )}
              {blockedCount > 0 && (
                <span className="rounded-full bg-amber-50 px-2.5 py-1 text-xs font-medium text-amber-700">
                  {blockedCount} impedida{blockedCount > 1 ? 's' : ''}
                </span>
              )}
            </div>
          </button>
        )
      })}
    </div>
  )
}
