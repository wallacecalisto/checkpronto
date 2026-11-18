import { Navigate, Route, Routes } from 'react-router-dom'
import { useAuth } from '../auth/useAuth'
import { AdminLayout } from '../components/admin/AdminLayout'
import { ChangePasswordPage } from '../pages/ChangePasswordPage'
import { LoginPage } from '../pages/Login'
import { AdminDashboardPage } from '../pages/admin/Dashboard'
import { AuditPage } from '../pages/admin/AuditPage'
import { ChecklistExecutionDetailPage } from '../pages/admin/ChecklistExecutionDetailPage'
import { ChecklistTemplateDetailPage } from '../pages/admin/ChecklistTemplateDetailPage'
import { ChecklistTemplatesPage } from '../pages/admin/ChecklistTemplatesPage'
import { ChecklistsPage } from '../pages/admin/ChecklistsPage'
import { EmployeesPage } from '../pages/admin/EmployeesPage'
import { SectorsPage } from '../pages/admin/SectorsPage'
import { StoreSettingsPage } from '../pages/admin/StoreSettingsPage'
import { StoresPage } from '../pages/admin/StoresPage'
import { TaskAssignmentsPage } from '../pages/admin/TaskAssignmentsPage'
import { TasksPage } from '../pages/admin/TasksPage'
import { UsersPage } from '../pages/admin/UsersPage'
import { OperationalHomePage } from '../pages/operational/Home'
import { ProtectedRoute } from './ProtectedRoute'
import { getHomePathForRole } from './roleHome'

export function AppRoutes() {
  const { isAuthenticated, user } = useAuth()

  return (
    <Routes>
      <Route
        path="/login"
        element={
          isAuthenticated && user ? <Navigate to={getHomePathForRole(user.role)} replace /> : <LoginPage />
        }
      />

      <Route element={<ProtectedRoute allowedRoles={['MASTER', 'GESTOR', 'LIDER']} />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin" element={<AdminDashboardPage />} />
          <Route path="/admin/employees" element={<EmployeesPage />} />
          <Route path="/admin/sectors" element={<SectorsPage />} />
          <Route path="/admin/tasks" element={<TasksPage />} />
          <Route path="/admin/agenda" element={<TaskAssignmentsPage />} />
          <Route path="/admin/checklists" element={<ChecklistsPage />} />
          <Route path="/admin/checklists/:id" element={<ChecklistExecutionDetailPage />} />
          {/* LIDER ganhou acesso ao catálogo de checklists — mesmo
              grupo de papéis do resto da gestão operacional do dia a dia. */}
          <Route path="/admin/checklist-templates" element={<ChecklistTemplatesPage />} />
          <Route path="/admin/checklist-templates/:id" element={<ChecklistTemplateDetailPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['MASTER', 'GESTOR']} />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin/logs" element={<AuditPage />} />
          <Route path="/admin/settings" element={<StoreSettingsPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute allowedRoles={['MASTER']} />}>
        <Route element={<AdminLayout />}>
          <Route path="/admin/stores" element={<StoresPage />} />
          <Route path="/admin/users" element={<UsersPage />} />
        </Route>
      </Route>

      <Route element={<ProtectedRoute />}>
        <Route path="/operacional" element={<OperationalHomePage />} />
      </Route>

      <Route element={<ProtectedRoute allowWhenPasswordChangeRequired />}>
        <Route path="/trocar-senha" element={<ChangePasswordPage />} />
      </Route>

      <Route
        path="/"
        element={
          isAuthenticated && user ? (
            <Navigate to={getHomePathForRole(user.role)} replace />
          ) : (
            <Navigate to="/login" replace />
          )
        }
      />

      <Route path="*" element={<Navigate to="/" replace />} />
    </Routes>
  )
}
