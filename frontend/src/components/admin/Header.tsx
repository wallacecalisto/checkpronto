import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { useSelectedStore } from '../../contexts/SelectedStoreContext'
import { useCurrentStore } from '../../hooks/useCurrentStore'
import { listStores } from '../../services/storeService'
import { MenuIcon, StoreIcon } from './icons'

function useStoreLabel(): string | null {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'

  const { data: ownStore } = useCurrentStore()
  const { storeId: selectedStoreId } = useSelectedStore()
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })

  if (isMaster) {
    if (selectedStoreId === null) return 'Todas as lojas'
    return storesQuery.data?.find((store) => store.id === selectedStoreId)?.name ?? 'Todas as lojas'
  }

  return ownStore?.name ?? null
}

interface HeaderProps {
  onOpenSidebar?: () => void
}

export function Header({ onOpenSidebar }: HeaderProps = {}) {
  const { user, logout } = useAuth()
  const storeLabel = useStoreLabel()

  return (
    <header className="flex items-center justify-between gap-4 border-b border-gray-100/50 bg-white px-4 py-4 shadow-sm sm:px-6">
      <div className="flex min-w-0 items-center gap-3">
        {onOpenSidebar && (
          <button
            type="button"
            onClick={onOpenSidebar}
            aria-label="Abrir menu"
            className="shrink-0 rounded-xl border border-gray-200 p-2 text-gray-600 transition-all duration-300 ease-in-out hover:bg-gray-100 md:hidden"
          >
            <MenuIcon className="h-5 w-5" />
          </button>
        )}
        {storeLabel && (
          <span className="inline-flex items-center gap-1.5 truncate rounded-full border border-emerald-100 bg-emerald-50 px-3 py-1 text-xs font-semibold text-emerald-700">
            <StoreIcon className="h-3.5 w-3.5 shrink-0" />
            {storeLabel}
          </span>
        )}
      </div>

      <div className="flex items-center gap-4">
        <div className="text-right">
          <p className="text-sm font-medium text-gray-900">{user?.name}</p>
          <p className="text-xs text-gray-500">{user?.role}</p>
        </div>
        <button
          type="button"
          onClick={() => void logout()}
          className="rounded-xl border border-gray-200 px-3 py-1.5 text-sm font-medium text-gray-600 transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-gray-100 hover:shadow-md"
        >
          Sair
        </button>
      </div>
    </header>
  )
}
