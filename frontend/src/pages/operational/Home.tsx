import { useMemo, useState } from 'react'
import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { StoreIcon } from '../../components/admin/icons'
import { useCurrentStore } from '../../hooks/useCurrentStore'
import { listActiveEmployees } from '../../services/employeeService'
import { listSectors } from '../../services/sectorService'
import { getStoreSettings } from '../../services/storeSettingsService'
import { listTaskAssignments } from '../../services/taskAssignmentService'
import type { Sector } from '../../types/sector'
import { LivePanel } from './LivePanel'
import { SectorGrid } from './SectorGrid'
import { SectorView } from './SectorView'

export function OperationalHomePage() {
  const { user, logout } = useAuth()
  const { data: store } = useCurrentStore()
  const [selectedSector, setSelectedSector] = useState<Sector | null>(null)

  const employeesQuery = useQuery({
    queryKey: ['employees', 'active'],
    queryFn: listActiveEmployees,
  })

  const sectorsQuery = useQuery({
    queryKey: ['sectors', 'operational'],
    queryFn: () => listSectors({ activeOnly: true }),
  })

  const storeSettingsQuery = useQuery({
    queryKey: ['store-settings', store?.id],
    queryFn: () => getStoreSettings(store!.id),
    enabled: store?.id !== undefined,
  })
  const checklistsEnabled = storeSettingsQuery.data?.operational_checklists_enabled ?? true
  const hideTaskTimer = storeSettingsQuery.data?.hide_task_timer ?? false
  const autoLogoutMinutes = storeSettingsQuery.data?.auto_logout_minutes ?? 5
  const requireLivePhotoOnly = storeSettingsQuery.data?.require_live_photo_only ?? false
  const shifts = storeSettingsQuery.data?.shifts ?? ['Geral']
  const enableAudioAlerts = storeSettingsQuery.data?.enable_audio_alerts ?? false

  const assignmentsQuery = useQuery({
    queryKey: ['task-assignments', 'operational'],
    queryFn: () => listTaskAssignments({}),
    refetchInterval: 5000,
  })

  const employees = employeesQuery.data ?? []
  const sectors = sectorsQuery.data ?? []
  const assignments = assignmentsQuery.data ?? []

  const inProgressAssignments = useMemo(
    () => assignments.filter((assignment) => assignment.status === 'IN_PROGRESS'),
    [assignments],
  )

  const isLoading = employeesQuery.isLoading || sectorsQuery.isLoading || assignmentsQuery.isLoading

  return (
    <div className="min-h-screen bg-slate-50 pb-10">
      <header className="flex flex-wrap items-center justify-between gap-x-3 gap-y-2 border-b border-slate-100 bg-white px-4 py-4 shadow-sm sm:px-8">
        <div className="flex min-w-0 items-center gap-3">
          <img src="/logo.png" alt="CheckPronto" className="h-10 w-auto shrink-0 object-contain md:h-12" />
          {store?.name && (
            <span className="inline-flex min-w-0 items-center gap-1.5 truncate rounded-full border border-indigo-100 bg-indigo-50 px-3 py-1 text-xs font-semibold text-indigo-700">
              <StoreIcon className="h-3.5 w-3.5 shrink-0" />
              <span className="truncate">{store.name}</span>
            </span>
          )}
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="shrink-0 rounded-xl border border-slate-200 px-3 py-1.5 text-sm text-slate-600 transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-slate-100 hover:shadow-md"
        >
          <span className="sm:hidden">Sair</span>
          <span className="hidden sm:inline">Sair ({user?.name})</span>
        </button>
      </header>

      <main className="mx-auto flex max-w-5xl flex-col gap-8 px-4 py-6 sm:px-8">
        {isLoading ? (
          <p className="text-center text-slate-500">Carregando…</p>
        ) : selectedSector ? (
          <SectorView
            sector={selectedSector}
            employees={employees}
            assignments={assignments}
            shifts={shifts}
            checklistsEnabled={checklistsEnabled}
            hideTaskTimer={hideTaskTimer}
            requireLivePhotoOnly={requireLivePhotoOnly}
            autoLogoutMinutes={autoLogoutMinutes}
            enableAudioAlerts={enableAudioAlerts}
            onBack={() => setSelectedSector(null)}
          />
        ) : (
          <>
            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-800">Em andamento agora</h2>
              <LivePanel assignments={inProgressAssignments} hideTimer={hideTaskTimer} />
            </section>

            <section>
              <h2 className="mb-3 text-lg font-semibold text-slate-800">Selecione o setor</h2>
              <SectorGrid sectors={sectors} assignments={assignments} onSelect={setSelectedSector} />
            </section>
          </>
        )}
      </main>
    </div>
  )
}
