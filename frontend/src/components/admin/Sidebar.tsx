import type { ComponentType, SVGProps } from 'react'
import { Link, NavLink } from 'react-router-dom'
import { useAuth } from '../../auth/useAuth'
import type { UserRole } from '../../types/auth'
import {
  AuditIcon,
  CalendarIcon,
  ClipboardCheckIcon,
  HomeIcon,
  SectorsIcon,
  SettingsIcon,
  ShieldIcon,
  StoreIcon,
  TasksIcon,
  UsersIcon,
} from './icons'

interface NavItem {
  to: string
  label: string
  icon: ComponentType<SVGProps<SVGSVGElement>>
  roles: UserRole[]
  end?: boolean
}

interface NavGroup {
  // Nulo = item solto, sem cabeçalho de seção acima dele (ex.: "Painel").
  heading: string | null
  items: NavItem[]
}

const NAV_GROUPS: NavGroup[] = [
  {
    heading: null,
    items: [{ to: '/admin', label: 'Painel', icon: HomeIcon, roles: ['MASTER', 'GESTOR', 'LIDER'], end: true }],
  },
  {
    heading: 'Tarefas',
    items: [
      { to: '/admin/tasks', label: 'Catálogo de Tarefas', icon: TasksIcon, roles: ['MASTER', 'GESTOR', 'LIDER'] },
      { to: '/admin/agenda', label: 'Agendamento de Tarefas', icon: CalendarIcon, roles: ['MASTER', 'GESTOR', 'LIDER'] },
    ],
  },
  {
    heading: 'Checklists',
    items: [
      {
        to: '/admin/checklists',
        label: 'Execuções de Checklists',
        icon: ClipboardCheckIcon,
        roles: ['MASTER', 'GESTOR', 'LIDER'],
      },
      {
        to: '/admin/checklist-templates',
        label: 'Catálogo de Checklists',
        icon: ClipboardCheckIcon,
        roles: ['MASTER', 'GESTOR', 'LIDER'],
      },
    ],
  },
  {
    heading: 'Administração',
    items: [
      { to: '/admin/sectors', label: 'Setores', icon: SectorsIcon, roles: ['MASTER', 'GESTOR', 'LIDER'] },
      { to: '/admin/employees', label: 'Funcionários', icon: UsersIcon, roles: ['MASTER', 'GESTOR', 'LIDER'] },
      { to: '/admin/stores', label: 'Lojas', icon: StoreIcon, roles: ['MASTER'] },
      { to: '/admin/users', label: 'Usuários', icon: ShieldIcon, roles: ['MASTER'] },
      { to: '/admin/logs', label: 'Logs', icon: AuditIcon, roles: ['MASTER', 'GESTOR'] },
      { to: '/admin/settings', label: 'Configurações', icon: SettingsIcon, roles: ['MASTER', 'GESTOR'] },
    ],
  },
]

interface SidebarProps {
  isOpen?: boolean
  onClose?: () => void
}

export function Sidebar({ isOpen = false, onClose = () => {} }: SidebarProps) {
  const { user } = useAuth()

  const groups = NAV_GROUPS.map((group) => ({
    heading: group.heading,
    items: group.items.filter((item) => user && item.roles.includes(user.role)),
  })).filter((group) => group.items.length > 0)

  return (
    <>
      {isOpen && (
        <div
          className="fixed inset-0 z-40 bg-black/50 md:hidden"
          onClick={onClose}
          aria-hidden="true"
        />
      )}

      <aside
        className={`fixed inset-y-0 left-0 z-50 flex w-64 shrink-0 -translate-x-full flex-col overflow-y-auto bg-slate-900 px-4 py-6 transition-transform duration-300 ease-in-out md:static md:translate-x-0 ${
          isOpen ? 'translate-x-0' : ''
        }`}
      >
        <div className="mb-8 flex justify-center">
          <Link
            to="/admin"
            onClick={onClose}
            className="rounded-2xl bg-white p-2.5 shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:shadow-md"
          >
            <img src="/logo.png" alt="CheckPronto" className="h-9 w-auto object-contain" />
          </Link>
        </div>

        <nav className="flex flex-col gap-5">
          {groups.map((group, index) => (
            <div key={group.heading ?? `top-${index}`} className="flex flex-col gap-1">
              {group.heading && (
                <p className="px-3 pb-1 text-xs font-semibold uppercase tracking-wider text-slate-500">
                  {group.heading}
                </p>
              )}
              {group.items.map((item) => (
                <NavLink
                  key={item.to}
                  to={item.to}
                  end={item.end}
                  onClick={onClose}
                  className={({ isActive }) =>
                    `flex items-center gap-3 rounded-xl px-3 py-2.5 text-sm font-medium transition-all duration-300 ease-in-out ${
                      isActive
                        ? 'bg-emerald-500/15 text-emerald-400'
                        : 'text-slate-300 hover:-translate-y-0.5 hover:bg-slate-800 hover:text-white'
                    }`
                  }
                >
                  <item.icon className="h-5 w-5 shrink-0" />
                  {item.label}
                </NavLink>
              ))}
            </div>
          ))}
        </nav>
      </aside>
    </>
  )
}
