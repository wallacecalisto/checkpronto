import { createContext, useCallback, useEffect, useMemo, useState, type ReactNode } from 'react'
import { apiClient, registerAuthHandlers, setAccessToken } from '../services/apiClient'
import type { LoginResponse, User } from '../types/auth'

export interface AuthContextValue {
  user: User | null
  isAuthenticated: boolean
  isLoading: boolean
  login: (email: string, password: string) => Promise<User>
  logout: () => Promise<void>
  setUser: (user: User) => void
}

export const AuthContext = createContext<AuthContextValue | undefined>(undefined)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    registerAuthHandlers({
      onTokenRefreshed: (refreshedUser) => setUser(refreshedUser),
      onSessionExpired: () => setUser(null),
    })
  }, [])

  useEffect(() => {
    let cancelled = false

    apiClient
      .post<LoginResponse>('/auth/refresh')
      .then((response) => {
        if (cancelled) return
        setAccessToken(response.data.access_token)
        setUser(response.data.user)
      })
      .catch(() => {
        if (!cancelled) setAccessToken(null)
      })
      .finally(() => {
        if (!cancelled) setIsLoading(false)
      })

    return () => {
      cancelled = true
    }
  }, [])

  const login = useCallback(async (email: string, password: string): Promise<User> => {
    const response = await apiClient.post<LoginResponse>('/auth/login', { email, password })
    setAccessToken(response.data.access_token)
    setUser(response.data.user)
    return response.data.user
  }, [])

  const logout = useCallback(async (): Promise<void> => {
    try {
      await apiClient.post('/auth/logout')
    } finally {
      setAccessToken(null)
      setUser(null)
    }
  }, [])

  const value = useMemo<AuthContextValue>(
    () => ({ user, isAuthenticated: user !== null, isLoading, login, logout, setUser }),
    [user, isLoading, login, logout],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}
