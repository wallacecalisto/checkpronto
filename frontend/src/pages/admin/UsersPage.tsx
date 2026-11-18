import { useState } from 'react'
import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useAuth } from '../../auth/useAuth'
import { ConfirmDeleteModal } from '../../components/admin/ConfirmDeleteModal'
import { TrashIcon } from '../../components/icons/TrashIcon'
import { getApiErrorMessage } from '../../services/apiClient'
import { listStores } from '../../services/storeService'
import { deleteUser, listUsers, updateUser } from '../../services/userService'
import type { User } from '../../types/auth'
import { UserFormModal } from './UserFormModal'

const ROLE_LABEL: Record<string, string> = {
  MASTER: 'Master',
  GESTOR: 'Gestor',
  LIDER: 'Líder',
  OPERACIONAL: 'Operacional',
}

type FormState = { mode: 'create' } | { mode: 'edit'; user: User } | null

export function UsersPage() {
  const { user: currentUser } = useAuth()
  const queryClient = useQueryClient()
  const [formState, setFormState] = useState<FormState>(null)
  const [showInactive, setShowInactive] = useState(false)
  const [userToDelete, setUserToDelete] = useState<User | null>(null)
  const [deleteErrorMessage, setDeleteErrorMessage] = useState<string | null>(null)

  const usersQuery = useQuery({ queryKey: ['users', 'admin'], queryFn: listUsers })
  const storesQuery = useQuery({ queryKey: ['stores'], queryFn: listStores })

  const toggleActiveMutation = useMutation({
    mutationFn: ({ id, active }: { id: number; active: boolean }) => updateUser(id, { active }),
    onSuccess: () => queryClient.invalidateQueries({ queryKey: ['users', 'admin'] }),
  })

  const deleteMutation = useMutation({
    mutationFn: (id: number) => deleteUser(id),
    onSuccess: () => {
      queryClient.invalidateQueries({ queryKey: ['users', 'admin'] })
      setUserToDelete(null)
      setDeleteErrorMessage(null)
    },
    onError: (error: unknown) => setDeleteErrorMessage(getApiErrorMessage(error)),
  })

  const allUsers = usersQuery.data ?? []
  const users = showInactive ? allUsers : allUsers.filter((userRow) => userRow.active)
  const stores = storesQuery.data ?? []
  const storeNameById = new Map(stores.map((store) => [store.id, store.name]))

  return (
    <div className="flex flex-col gap-6">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="text-xl font-semibold text-gray-900">Usuários</h1>
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
            Novo Acesso
          </button>
        </div>
      </div>

      <div className="overflow-x-auto rounded-2xl border border-gray-100/50 bg-white shadow-sm transition-all duration-300 ease-in-out hover:shadow-md">
        <table className="w-full text-left text-sm">
          <thead className="border-b border-gray-200 text-gray-500">
            <tr>
              <th className="px-4 py-3 font-medium">Nome</th>
              <th className="px-4 py-3 font-medium">E-mail</th>
              <th className="px-4 py-3 font-medium">Papel</th>
              <th className="px-4 py-3 font-medium">Loja</th>
              <th className="px-4 py-3 font-medium">Status</th>
              <th className="px-4 py-3 font-medium">Ações</th>
            </tr>
          </thead>
          <tbody>
            {usersQuery.isLoading && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Carregando…
                </td>
              </tr>
            )}
            {!usersQuery.isLoading && users.length === 0 && (
              <tr>
                <td colSpan={6} className="px-4 py-6 text-center text-gray-500">
                  Nenhum usuário cadastrado.
                </td>
              </tr>
            )}
            {users.map((userRow) => (
              <tr key={userRow.id} className="border-b border-gray-100 transition-colors duration-300 last:border-0 hover:bg-gray-50">
                <td className="px-4 py-3 font-medium text-gray-900">{userRow.name}</td>
                <td className="px-4 py-3 text-gray-600">{userRow.email}</td>
                <td className="px-4 py-3 text-gray-600">{ROLE_LABEL[userRow.role] ?? userRow.role}</td>
                <td className="px-4 py-3 text-gray-600">
                  {userRow.store_id ? (storeNameById.get(userRow.store_id) ?? '—') : 'Todas (global)'}
                </td>
                <td className="px-4 py-3">
                  {userRow.active ? (
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
                  <div className="flex gap-2">
                    <button
                      type="button"
                      onClick={() => setFormState({ mode: 'edit', user: userRow })}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100"
                    >
                      Editar
                    </button>
                    <button
                      type="button"
                      onClick={() => toggleActiveMutation.mutate({ id: userRow.id, active: !userRow.active })}
                      disabled={toggleActiveMutation.isPending}
                      className="rounded-lg border border-gray-200 px-3 py-1.5 text-xs font-medium text-gray-600 transition hover:bg-gray-100 disabled:cursor-not-allowed disabled:opacity-50"
                    >
                      {userRow.active ? 'Desativar' : 'Reativar'}
                    </button>
                    {userRow.id !== currentUser?.id && (
                      <button
                        type="button"
                        onClick={() => {
                          setDeleteErrorMessage(null)
                          setUserToDelete(userRow)
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
        <UserFormModal
          {...(formState.mode === 'create' ? { mode: 'create' } : { mode: 'edit', user: formState.user })}
          stores={stores}
          onClose={() => setFormState(null)}
        />
      )}

      {userToDelete && (
        <ConfirmDeleteModal
          title="Excluir usuário"
          message={
            <>
              Tem certeza que deseja excluir <strong>{userToDelete.name}</strong>? O acesso dele(a) é revogado
              imediatamente; o histórico de ações e checklists já feitos por ele(a) é mantido.
            </>
          }
          isSubmitting={deleteMutation.isPending}
          errorMessage={deleteErrorMessage}
          onConfirm={() => deleteMutation.mutate(userToDelete.id)}
          onClose={() => setUserToDelete(null)}
        />
      )}
    </div>
  )
}
