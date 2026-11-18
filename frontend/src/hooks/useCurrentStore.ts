import { useQuery } from '@tanstack/react-query'
import { useAuth } from '../auth/useAuth'
import { getStore } from '../services/storeService'

export function useCurrentStore() {
  const { user } = useAuth()
  const storeId = user?.store_id ?? null

  return useQuery({
    queryKey: ['store', 'current', storeId],
    queryFn: () => getStore(storeId as number),
    enabled: storeId !== null,
  })
}
