import axios, { type AxiosRequestConfig, type InternalAxiosRequestConfig } from 'axios'
import type { ApiErrorBody, LoginResponse, User } from '../types/auth'

const API_BASE_URL = import.meta.env.VITE_API_BASE_URL ?? 'http://localhost:8000/api/v1'

export const apiClient = axios.create({
  baseURL: API_BASE_URL,
  withCredentials: true,
})

let currentAccessToken: string | null = null

export function setAccessToken(token: string | null): void {
  currentAccessToken = token
}

apiClient.interceptors.request.use((config) => {
  if (currentAccessToken) {
    config.headers.Authorization = `Bearer ${currentAccessToken}`
  }
  return config
})

let onTokenRefreshed: ((user: User) => void) | null = null
let onSessionExpired: (() => void) | null = null

export function registerAuthHandlers(handlers: {
  onTokenRefreshed?: (user: User) => void
  onSessionExpired?: () => void
}): void {
  onTokenRefreshed = handlers.onTokenRefreshed ?? null
  onSessionExpired = handlers.onSessionExpired ?? null
}

let refreshPromise: Promise<string | null> | null = null

async function refreshAccessToken(): Promise<string | null> {
  // Se várias chamadas falharem com 401 ao mesmo tempo, só um /auth/refresh
  // de verdade é disparado — as outras esperam o mesmo resultado.
  if (refreshPromise) {
    return refreshPromise
  }

  refreshPromise = axios
    .post<LoginResponse>(`${API_BASE_URL}/auth/refresh`, {}, { withCredentials: true })
    .then((response) => {
      setAccessToken(response.data.access_token)
      onTokenRefreshed?.(response.data.user)
      return response.data.access_token
    })
    .catch(() => {
      setAccessToken(null)
      onSessionExpired?.()
      return null
    })
    .finally(() => {
      refreshPromise = null
    })

  return refreshPromise
}

interface RetryableConfig extends InternalAxiosRequestConfig {
  _retry?: boolean
}

apiClient.interceptors.response.use(
  (response) => response,
  async (error: unknown) => {
    if (!axios.isAxiosError(error) || !error.config) {
      return Promise.reject(error)
    }

    const originalRequest = error.config as RetryableConfig
    const isAuthEndpoint = originalRequest.url?.includes('/auth/login') || originalRequest.url?.includes('/auth/refresh')

    if (error.response?.status === 401 && !originalRequest._retry && !isAuthEndpoint) {
      originalRequest._retry = true
      const newToken = await refreshAccessToken()
      if (newToken) {
        originalRequest.headers.Authorization = `Bearer ${newToken}`
        return apiClient(originalRequest as AxiosRequestConfig)
      }
    }

    return Promise.reject(error)
  },
)

// Extrai a mensagem/código padronizados do backend (ver app/core/errors.py) —
// nunca deixa cada tela reimplementar esse parsing.
export function getApiErrorMessage(error: unknown): string {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined
    if (body?.detail) return body.detail
    if (!error.response) {
      return 'Não foi possível conectar ao servidor. Verifique sua conexão e tente novamente.'
    }
  }
  return 'Não foi possível completar a ação. Tente novamente.'
}

export function getApiErrorCode(error: unknown): string | null {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined
    return body?.code ?? null
  }
  return null
}

export function getApiErrorField(error: unknown, field: string): string | null {
  if (axios.isAxiosError(error)) {
    const body = error.response?.data as ApiErrorBody | undefined
    const value = body?.[field]
    return typeof value === 'string' ? value : null
  }
  return null
}
