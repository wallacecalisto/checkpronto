import { createContext, useContext, useMemo, useState, type ReactNode } from 'react'

interface SelectedStoreContextValue {
  storeId: number | null
  setStoreId: (storeId: number | null) => void
}

const SelectedStoreContext = createContext<SelectedStoreContextValue | null>(null)

export function SelectedStoreProvider({ children }: { children: ReactNode }) {
  const [storeId, setStoreId] = useState<number | null>(null)
  const value = useMemo(() => ({ storeId, setStoreId }), [storeId])

  return <SelectedStoreContext.Provider value={value}>{children}</SelectedStoreContext.Provider>
}

export function useSelectedStore(): SelectedStoreContextValue {
  const context = useContext(SelectedStoreContext)
  if (!context) {
    throw new Error('useSelectedStore deve ser usado dentro de um SelectedStoreProvider')
  }
  return context
}
