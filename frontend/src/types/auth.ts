// Espelha app/schemas/user.py e app/models/user.py (backend) — mesmos papéis,
// mesmos campos. Se um papel novo for adicionado lá, precisa ser adicionado aqui também.
export type UserRole = 'MASTER' | 'GESTOR' | 'LIDER' | 'OPERACIONAL'

export interface User {
  id: number
  name: string
  email: string
  role: UserRole
  store_id: number | null
  active: boolean
  must_change_password: boolean
}

// Espelha app/schemas/auth.py::TokenResponse
export interface LoginResponse {
  access_token: string
  token_type: string
  user: User
}

// Espelha o formato padrão de erro em app/core/errors.py. Alguns erros vêm
// com campos extras (ex.: "locked_until" no PIN_LOCKED) além de detail/code.
export interface ApiErrorBody {
  detail: string
  code: string
  errors?: unknown
  [key: string]: unknown
}
