import { useState, type FormEvent } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'
import { Modal } from '../../components/Modal'
import { getApiErrorMessage } from '../../services/apiClient'
import { createUser, updateUser } from '../../services/userService'
import type { User, UserRole } from '../../types/auth'
import type { Store } from '../../types/store'

type UserFormModalProps = { stores: Store[]; onClose: () => void } & (
  | { mode: 'create' }
  | { mode: 'edit'; user: User }
)

const ROLE_OPTIONS: { value: UserRole; label: string }[] = [
  { value: 'MASTER', label: 'Master (acesso global, todas as lojas)' },
  { value: 'GESTOR', label: 'Gestor' },
  { value: 'LIDER', label: 'Líder' },
  { value: 'OPERACIONAL', label: 'Operacional (Área Operacional)' },
]

export function UserFormModal(props: UserFormModalProps) {
  const { stores, onClose } = props
  const existingUser = props.mode === 'edit' ? props.user : null

  const queryClient = useQueryClient()
  const [name, setName] = useState(existingUser?.name ?? '')
  const [email, setEmail] = useState(existingUser?.email ?? '')
  const [password, setPassword] = useState('')
  const [role, setRole] = useState<UserRole>(existingUser?.role ?? 'LIDER')
  const [storeId, setStoreId] = useState(existingUser?.store_id ? String(existingUser.store_id) : '')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)

  const requiresStore = role !== 'MASTER'

  const mutation = useMutation({
    mutationFn: async () => {
      if (existingUser) {
        return updateUser(existingUser.id, {
          name,
          role,
          store_id: requiresStore ? Number(storeId) : undefined,
          password: password || undefined,
        })
      }
      return createUser({
        name,
        email,
        password,
        role,
        store_id: requiresStore ? Number(storeId) : undefined,
      })
    },
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', 'admin'] })
      onClose()
    },
    onError: (error: unknown) => setErrorMessage(getApiErrorMessage(error)),
  })

  function handleSubmit(event: FormEvent<HTMLFormElement>): void {
    event.preventDefault()
    setErrorMessage(null)
    mutation.mutate()
  }

  function handleRoleChange(newRole: UserRole): void {
    setRole(newRole)
    if (newRole === 'MASTER') setStoreId('')
  }

  return (
    <Modal title={existingUser ? 'Editar acesso' : 'Novo acesso'} onClose={onClose}>
      <form onSubmit={handleSubmit} className="flex flex-col gap-4">
        <div className="flex flex-col gap-1.5">
          <label htmlFor="user-name" className="text-sm font-medium text-gray-700">
            Nome
          </label>
          <input
            id="user-name"
            required
            value={name}
            onChange={(event) => setName(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="user-email" className="text-sm font-medium text-gray-700">
            E-mail
          </label>
          <input
            id="user-email"
            type="email"
            required
            disabled={!!existingUser}
            value={email}
            onChange={(event) => setEmail(event.target.value)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20 disabled:cursor-not-allowed disabled:opacity-60"
          />
          {existingUser && <p className="text-xs text-gray-400">O e-mail não pode ser alterado depois de criado.</p>}
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="user-password" className="text-sm font-medium text-gray-700">
            Senha {existingUser ? '(deixe em branco para manter a atual)' : ''}
          </label>
          <input
            id="user-password"
            type="password"
            required={!existingUser}
            minLength={8}
            value={password}
            onChange={(event) => setPassword(event.target.value)}
            placeholder="Mínimo 8 caracteres"
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none placeholder:text-gray-400 focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          />
        </div>

        <div className="flex flex-col gap-1.5">
          <label htmlFor="user-role" className="text-sm font-medium text-gray-700">
            Papel
          </label>
          <select
            id="user-role"
            value={role}
            onChange={(event) => handleRoleChange(event.target.value as UserRole)}
            className="rounded-lg border border-gray-200 bg-gray-50 px-3 py-2 text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
          >
            {ROLE_OPTIONS.map((option) => (
              <option key={option.value} value={option.value}>
                {option.label}
              </option>
            ))}
          </select>
        </div>

        {requiresStore && (
          <div className="flex flex-col gap-1.5">
            <label htmlFor="user-store" className="text-sm font-medium text-gray-700">
              Loja
            </label>
            <select
              id="user-store"
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
