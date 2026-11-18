import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { ConfirmDeleteModal } from '../../components/admin/ConfirmDeleteModal'
import { TrashIcon } from '../../components/icons/TrashIcon'
import { getApiErrorMessage } from '../../services/apiClient'
import { deleteEmployee, listEmployees, resetPin, updateEmployee } from '../../services/employeeService'
import { listSectors } from '../../services/sectorService'
import { listStores } from '../../services/storeService'
import type { Employee } from '../../types/employee'
import { EmployeeFormModal } from './EmployeeFormModal'

type FormState = { mode: 'create' } | { mode: 'edit'; employee: Employee } | null

export function EmployeesPage() {
  const { user } = useAuth()
  const isMaster = user?.role === 'MASTER'
  const canResetPin = user?.role === 'MASTER' || user?.role === 'GESTOR' || user?.role === 'LIDER'
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<FormState>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [employeeToDelete, setEmployeeToDelete] = useState<Employee | null>(null)
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null)

  const employeesQuery = useQuery({ queryKey: ['employees', 'admin'], queryFn: () => listEmployees() })
  // GET /stores é restrito a MASTER no backend — só busca quando faz sentido.
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores, enabled: isMaster })
  const sectorsQuery = useQuery({ queryKey: ['sectors', 'admin'], queryFn: () => listSectors() })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateEmployee(id, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees', 'admin'] }),
  })

  const resetPinMutation = useMutation({
    mutationFn: (id: number) => resetPin(id),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['employees', 'admin'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteEmployee(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', 'admin'] })
      setEmployeeToDelete(null)
      setDeleteErrorMessage(null)
    },
    onError: (error: unknown) => setDeleteErrorMessage(getApiErrorMessage(error)),
  })

  const allEmployees = employeesQuery.data ?? []
  const employees = showInactive ? allEmployees : allEmployees.filter((employee) => employee.active)
  const stores = storesQuery.data ?? []
  const sectors = sectorsQuery.data ?? []
  const sectorNameById = new Map(sectors.map((sector) => [sector.id, sector.name]))

  function handleResetPin(employee: Employee): void {
    const confirmed = window.confirm(`Resetar o PIN de ${employee.name}? Ele(a) vai precisar criar um novo PIN.`)
    if (!confirmed) return
    setErrorMessage(null)
    resetPinMutation.mutate(employee.id)
  }

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Funcionários</h1>
        <div className="flex items-center gap-4">
          <label className="flex items-center gap-2 text-sm text-gray-600">
            <input
              type="checkbox"
              checked={showInactive}
              onChange={(event) => setShowInactive(event.target.checked)}
              className="h-4 w-4 rounded border-gray-300 text-emerald-500 focus:ring-emerald-500/40"
            />
            Mostrar inativos
          </label>
          <button
            type="button"
            onClick={() => setFormState({ mode: 'create' })}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md"
          >
            Novo Funcionário
          </button>
        </div>
      </div>

      {errorMessage && (
        <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
          {errorMessage}
        </p>
      )}

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">Cargo</th>
              <th className="px-4 py-3 font-medium">Setor</th>
              <th className="px-4 py-3 font-medium">PIN</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {employeesQuery.isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!employeesQuery.isLoading && employees.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Nenhum funcionário cadastrado.
                </td>
              </tr>
            )}
            {employees.map((employee) => (
              <tr key={employee.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{employee.name}</td>
                <td className="px-4 py-3 text-gray-600">{employee.role_title ?? '—'}</td>
                <td className="px-4 py-3 text-gray-600">{sectorNameById.get(employee.sector_id) ?? '—'}</td>
                <td className="px-4 py-3">
                  {employee.has_pin ? (
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                      Definido
                    </span>
                  ) : (
                    <span className="rounded-full bg-orange-50 px-2.5 py-1 text-xs font-medium text-orange-600">
                      Sem PIN
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  {employee.active ? (
                    <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs font-medium text-emerald-600">
                      Ativo
                    </span>
                  ) : (
                    <span className="rounded-full bg-gray-100 px-2.5 py-1 text-xs font-medium text-gray-500">
                      Inativo
                    </span>
                  )}
                </td>
                <td className="px-4 py-3">
                  <div className="flex flex-wrap gap-2">
                    <button
                      type="button"
                      onClick={() => setFormState({ mode: 'edit', employee })}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Editar
                    </button>
                    {canResetPin && (
                      <button
                        type="button"
                        onClick={() => handleResetPin(employee)}
                        disabled={!employee.has_pin || resetPinMutation.isPending}
                        className="rounded-lg border border-orange-200 px-3 py-1.5 text-xs font-medium text-orange-600 transition hover:bg-orange-50 disabled:cursor-not-allowed disabled:opacity-50"
                      >
                        Resetar PIN
                      </button>
                    )}
                    <button
                      type="button"
                      onClick={() => toggleActiveMutation.mutate({ id: employee.id, active: !employee.active })}
                      disabled={toggleActiveMutation.isPending}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {employee.active ? 'Desativar' : 'Ativar'}
                    </button>
                    {isMaster && (
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteErrorMessage(null)
                          setEmployeeToDelete(employee)
                        }}
                        className="flex items-center gap-1 rounded-lg border border-red-200 px-3 py-1.5 text-xs font-medium text-red-600 transition hover:bg-red-50"
                      >
                        <TrashIcon className="h-3.5 w-3.5" />
                        Excluir
                      </button>
                    )}
                  </div>
                </td>
              </tr>
            ))}
          </tbody>
        </table>
      </div>

      {formState && (
        <EmployeeFormModal
          {...(formState.mode === 'create' ? { mode: 'create' } : { mode: 'edit', employee: formState.employee })}
          stores={stores}
          isMaster={isMaster}
          onClose={() => setFormState(null)}
        />
      )}

      {employeeToDelete && (
        <ConfirmDeleteModal
          title="Excluir funcionário"
          message={
            <>
              Tem certeza que deseja excluir <strong>{employeeToDelete.name}</strong>? O histórico de tarefas e
              checklists dele(a) é mantido, mas ele(a) some da lista e não pode mais bater PIN.
            </>
          }
          isSubmitting={deleteMutation.isPending}
          errorMessage={deleteErrorMessage}
          onConfirm={() => deleteMutation.mutate(employeeToDelete.id)}
          onClose={() => setEmployeeToDelete(null)}
        />
      )}
    </div>
  )
}
