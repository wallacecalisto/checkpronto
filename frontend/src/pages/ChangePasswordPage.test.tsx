import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter, Route, Routes } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import type { User } from '../types/auth'
import { ChangePasswordPage } from './ChangePasswordPage'

const mockChangePassword = vi.fn()
const mockSetUser = vi.fn()

vi.mock('../services/authService', () => ({
  changePassword: (...args: unknown[]) => mockChangePassword(...args),
}))

const currentUser: User = {
  id: 1,
  name: 'Gestora',
  email: 'gestora@kijapa.com',
  role: 'GESTOR',
  store_id: 1,
  active: true,
  must_change_password: true,
}

vi.mock('../auth/useAuth', () => ({
  useAuth: () => ({
    user: currentUser,
    isAuthenticated: true,
    isLoading: false,
    login: vi.fn(),
    logout: vi.fn(),
    setUser: mockSetUser,
  }),
}))

function renderPage() {
  return render(
    <MemoryRouter initialEntries={['/trocar-senha']}>
      <Routes>
        <Route path="/trocar-senha" element={<ChangePasswordPage />} />
        <Route path="/admin" element={<div>Painel administrativo</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('ChangePasswordPage', () => {
  beforeEach(() => {
    mockChangePassword.mockReset()
    mockSetUser.mockReset()
  })

  it('envia a senha atual e a nova para o serviço e navega para a home do papel ao ter sucesso', async () => {
    const updatedUser: User = { ...currentUser, must_change_password: false }
    mockChangePassword.mockResolvedValueOnce(updatedUser)
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Senha atual'), 'SenhaTemporaria123')
    await user.type(screen.getByLabelText('Nova senha'), 'NovaSenhaForte123')
    await user.type(screen.getByLabelText('Confirme a nova senha'), 'NovaSenhaForte123')
    await user.click(screen.getByRole('button', { name: 'Salvar nova senha' }))

    await waitFor(() => {
      expect(mockChangePassword).toHaveBeenCalledWith({
        current_password: 'SenhaTemporaria123',
        new_password: 'NovaSenhaForte123',
      })
    })
    await waitFor(() => expect(mockSetUser).toHaveBeenCalledWith(updatedUser))
    expect(await screen.findByText('Painel administrativo')).toBeInTheDocument()
  })

  it('mostra erro e não chama o serviço quando a confirmação não confere com a nova senha', async () => {
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Senha atual'), 'SenhaTemporaria123')
    await user.type(screen.getByLabelText('Nova senha'), 'NovaSenhaForte123')
    await user.type(screen.getByLabelText('Confirme a nova senha'), 'OutraSenhaQualquer')
    await user.click(screen.getByRole('button', { name: 'Salvar nova senha' }))

    expect(await screen.findByRole('alert')).toHaveTextContent('As senhas novas não conferem.')
    expect(mockChangePassword).not.toHaveBeenCalled()
  })

  it('mostra a mensagem de erro vinda da API quando o serviço rejeita (ex.: senha atual errada)', async () => {
    mockChangePassword.mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Senha atual incorreta.', code: 'INVALID_CREDENTIALS' } },
    })
    const user = userEvent.setup()
    renderPage()

    await user.type(screen.getByLabelText('Senha atual'), 'SenhaErrada')
    await user.type(screen.getByLabelText('Nova senha'), 'NovaSenhaForte123')
    await user.type(screen.getByLabelText('Confirme a nova senha'), 'NovaSenhaForte123')
    await user.click(screen.getByRole('button', { name: 'Salvar nova senha' }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/senha atual incorreta/i)
  })
})
