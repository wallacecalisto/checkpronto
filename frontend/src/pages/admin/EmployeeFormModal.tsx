import { useEffect, useState, type FormEvent } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { Modal } from '../../components/Modal'
import { getApiErrorMessage } from '../../services/apiClient'
import { createEmployee, updateEmployee } from '../../services/employeeService'
import { listSectors } from '../../services/sectorService'
import type { Employee } from '../../types/employee'
import type { Store } from '../../types/store'

type EmployeeFormModalProps = { stores: Store[]; isMaster: boolean; onClose: () => void } & (
  | { mode: 'create' }
  | { mode: 'edit'; employee: Employee }
)

export function EmployeeFormModal(props: EmployeeFormModalProps) {
  const { stores, isMaster, onClose } = props
  const existingEmployee = props.mode === 'edit' ? props.employee : null
  const { user } = useAuth()

  const queryClient = useQueryClient()
  const [name, setName] = useState(existingEmployee?.name ?? '')
  const [roleTitle, setRoleTitle] = useState(existingEmployee?.role_title ?? '')
  const [storeId, setStoreId] = useState('')
  const [sectorId, setSectorId] = useState(existingEmployee?.sector_id ? String(existingEmployee.sector_id) : '')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const sectorsStoreId = existingEmployee
    ? existingEmployee.store_id
    : isMaster
      ? (storeId ? Number(storeId) : undefined)
      : user?.store_id ?? undefined
  const sectorsQuery = useQuery({
    queryKey: ['sectors', 'for-employee-form', sectorsStoreId],
    queryFn: () => listSectors({ activeOnly: true, storeId: sectorsStoreId }),
    enabled: sectorsStoreId !== undefined,
  })
  const sectors = sectorsQuery.data ?? []

  useEffect(() => {
    if (!existingEmployee) setSectorId('')
  }, [sectorsStoreId, existingEmployee])

  const mutation = useMutation({
    mutationFn: async () => {
      if (existingEmployee) {
        return updateEmployee(existingEmployee.id, {
          name,
          role_title: roleTitle || null,
          sector_id: Number(sectorId),
        })
      }
      return createEmployee({
        name,
        role_title: roleTitle || undefined,
        store_id: isMaster ? Number(storeId) : undefined,
        sector_id: Number(sectorId),
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['employees', 'admin'] })
      onClose()
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setErrorMessage(null)
    mutation.mutate()
  }

  return (
    <Modal title={existingEmployee ? 'Editar funcionário' : 'Novo funcionário'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="employee-name" className="text-sm font-medium text-gray-700">
            Nome
          </label>
          <input
            id="employee-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="employee-role" className="text-sm font-medium text-gray-700">
            Cargo (opcional)
          </label>
          <input
            id="employee-role"
            value={roleTitle}
            onChange={(event) => setRoleTitle(event.target.value)}
            placeholder="Ex.: Cozinheiro"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        {!existingEmployee && isMaster && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="employee-store" className="text-sm font-medium text-gray-700">
              Loja
            </label>
            <select
              id="employee-store"
              required
              value={storeId}
              onChange={(event) => setStoreId(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            >
              <option value="" disabled>
                Selecione…
              </option>
              {stores.map((store) => (
                <option key={store.id} value={store.id}>
                  {store.name}
                </option>
              ))}
            </select>
          </div>
        )}

        <div className="flex flex-col gap-1.5">
          <label htmlFor="employee-sector" className="text-sm font-medium text-gray-700">
            Setor
          </label>
          <select
            id="employee-sector"
            required
            value={sectorId}
            onChange={(event) => setSectorId(event.target.value)}
            disabled={sectorsStoreId === undefined}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          >
            <option value="" disabled>
              {sectorsStoreId === undefined ? 'Selecione a loja primeiro…' : 'Selecione…'}
            </option>
            {sectors.map((sector) => (
              <option key={sector.id} value={sector.id}>
                {sector.name}
              </option>
            ))}
          </select>
        </div>

        {errorMessage && (
          <p role="alert" className="rounded-lg bg-red-50 px-3 py-2 text-sm text-red-600">
            {errorMessage}
          </p>
        )}

        <div className="mt-2 flex justify-end gap-2">
          <button
            type="button"
            onClick={onClose}
            className="rounded-lg border border-gray-200 px-4 py-2 text-sm font-medium text-gray-600 transition hover:bg-gray-100"
          >
            Cancelar
          </button>
          <button
            type="submit"
            disabled={mutation.isPending}
            className="rounded-xl bg-emerald-500 px-4 py-2 text-sm font-semibold text-white shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:bg-emerald-600 hover:shadow-md disabled:cursor-not-allowed disabled:opacity-60"
          >
            {mutation.isPending ? 'Salvando…' : 'Salvar'}
          </button>
        </div>
      </form>
    </Modal>
  )
}
