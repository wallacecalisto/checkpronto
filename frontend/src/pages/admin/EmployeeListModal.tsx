import { useQuery } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { listEmployees } from '../../services/employeeService'

interface EmployeeListModalProps {
  storeId?: number
  onSelectEmployee: (employee: { id: number; name: string }) => void
  onClose: () => void
}

export function EmployeeListModal({ storeId, onSelectEmployee, onClose }: EmployeeListModalProps) {
  const employeesQuery = useQuery({
    queryKey: ['employees', 'list-modal', storeId],
    queryFn: () => listEmployees({ activeOnly: true, storeId }),
  })
  const employees = employeesQuery.data ?? []

  return (
    <Modal title="Lista de Funcionários" onClose={onClose}>
      {employeesQuery.isLoading ? (
        <p className="text-sm text-gray-400">Carregando…</p>
      ) : employees.length === 0 ? (
        <p className="text-sm text-gray-400">Nenhum funcionário ativo cadastrado.</p>
      ) : (
        <ul className="flex max-h-96 flex-col gap-1 overflow-y-auto">
          {employees.map((employee) => (
            <li key={employee.id}>
              <button
                type="button"
                onClick={() => onSelectEmployee({ id: employee.id, name: employee.name })}
                className="flex w-full items-center justify-between gap-3 rounded-xl p-2.5 text-left transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-gray-50 hover:shadow-md"
              >
                <span className="truncate text-sm font-medium text-gray-900">{employee.name}</span>
                {employee.role_title && <span className="shrink-0 text-xs text-gray-500">{employee.role_title}</span>}
              </button>
            </li>
          ))}
        </ul>
      )}
    </Modal>
  )
}
