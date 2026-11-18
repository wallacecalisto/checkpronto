import { render, screen } from '@testing-library/react'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { describe, expect, it, vi } from 'vitest'
import { AuthContext, type AuthContextValue } from '../auth/AuthContext'
import type { User } from '../types/auth'
import { ProtectedRoute } from './ProtectedRoute'

function renderAsUser(user: User, initialPath: string) {
  const authValue: AuthContextValue = {
    user,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(async () => user),
    logout: vi.fn(async () => {}),
    setUser: vi.fn(),
  }

  return render(
    <AuthContext.Provider value={authValue}>
      <MemoryRouter initialEntries={[initialPath]}>
        <Routes>
          <Route element={<ProtectedRoute allowedRoles={['MASTER', 'GESTOR', 'LIDER']} />}>
            <Route path="/admin" element={<div>Painel administrativo</div>} />
          </Route>
          <Route element={<ProtectedRoute />}>
            <Route path="/operacional" element={<div>Tela operacional</div>} />
          </Route>
          <Route path="/trocar-senha" element={<div>Trocar senha</div>} />
        </Routes>
      </MemoryRouter>
    </AuthContext.Provider>,
  )
}

const operationalUser: User = {
  id: 2,
  name: 'Tablet Cozinha',
  email: 'tablet@kijapa.com',
  role: 'OPERACIONAL',
  store_id: 1,
  active: true,
  must_change_password: false,
}

const gestorUser: User = {
  id: 3,
  name: 'Gestora',
  email: 'gestora@kijapa.com',
  role: 'GESTOR',
  store_id: 1,
  active: true,
  must_change_password: false,
}

describe('ProtectedRoute', () => {
  it('bloqueia um usuário OPERACIONAL de acessar rota administrativa e o redireciona', () => {
    renderAsUser(operationalUser, '/admin')

    expect(screen.queryByText('Painel administrativo')).not.toBeInTheDocument()
    expect(screen.getByText('Tela operacional')).toBeInTheDocument()
  })

  it('permite que GESTOR acesse a rota administrativa normalmente', () => {
    renderAsUser(gestorUser, '/admin')

    expect(screen.getByText('Painel administrativo')).toBeInTheDocument()
  })

  it('redireciona para /login quando não há usuário autenticado', () => {
    render(
      <AuthContext.Provider
        value={{
          user: null,
          isAuthenticated: false,
          isLoading: false,
          login: vi.fn(),
          logout: vi.fn(),
          setUser: vi.fn(),
        }}
      >
        <MemoryRouter initialEntries={['/admin']}>
          <Routes>
            <Route path="/login" element={<div>Tela de login</div>} />
            <Route element={<ProtectedRoute allowedRoles={['MASTER']} />}>
              <Route path="/admin" element={<div>Painel administrativo</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    expect(screen.getByText('Tela de login')).toBeInTheDocument()
  })

  it('redireciona para /trocar-senha quando must_change_password é true, mesmo com papel permitido', () => {
    renderAsUser({ ...gestorUser, must_change_password: true }, '/admin')

    expect(screen.queryByText('Painel administrativo')).not.toBeInTheDocument()
    expect(screen.getByText('Trocar senha')).toBeInTheDocument()
  })

  it('permite acesso com allowWhenPasswordChangeRequired mesmo quando must_change_password é true', () => {
    const user: User = { ...gestorUser, must_change_password: true }
    const authValue: AuthContextValue = {
      user,
      isAuthenticated: true,
      isLoading: false,
      login: vi.fn(async () => user),
      logout: vi.fn(async () => {}),
      setUser: vi.fn(),
    }

    render(
      <AuthContext.Provider value={authValue}>
        <MemoryRouter initialEntries={['/trocar-senha']}>
          <Routes>
            <Route element={<ProtectedRoute allowWhenPasswordChangeRequired />}>
              <Route path="/trocar-senha" element={<div>Formulário de troca de senha</div>} />
            </Route>
          </Routes>
        </MemoryRouter>
      </AuthContext.Provider>,
    )

    expect(screen.getByText('Formulário de troca de senha')).toBeInTheDocument()
  })
})
