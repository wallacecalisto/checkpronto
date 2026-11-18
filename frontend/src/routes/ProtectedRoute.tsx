import { Navigate, Outlet, useLocation } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import type { UserRole } from '../types/auth'
import { getHomePathForRole } from './roleHome'

interface ProtectedRouteProps {
  allowedRoles?: UserRole[]
  allowWhenPasswordChangeRequired?: boolean
}

export function ProtectedRoute({ allowedRoles, allowWhenPasswordChangeRequired }: ProtectedRouteProps) {
  const { user, isAuthenticated, isLoading } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return (
      <div className="flex min-h-screen items-center justify-center bg-slate-50 text-slate-500">
        Carregando…
      </div>
    )
  }

  if (!isAuthenticated || user === null) {
    return <Navigate to="/login" replace state={{ from: location }} />
  }

  if (user.must_change_password && !allowWhenPasswordChangeRequired) {
    return <Navigate to="/trocar-senha" replace />
  }

  if (allowedRoles && !allowedRoles.includes(user.role)) {
    return <Navigate to={getHomePathForRole(user.role)} replace />
  }

  return <Outlet />
}
