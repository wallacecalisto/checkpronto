import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { MemoryRouter } from 'react-router-dom'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { AuthProvider } from '../auth/AuthContext'
import { LoginPage } from './Login'

const mockPost = vi.fn()

vi.mock('../services/apiClient', () => ({
  apiClient: { post: (...args: unknown[]) => mockPost(...args) },
  setAccessToken: vi.fn(),
  registerAuthHandlers: vi.fn(),
  getApiErrorMessage: () => 'E-mail ou senha inválidos.',
}))

function renderLoginPage() {
  return render(
    <MemoryRouter initialEntries={['/login']}>
      <AuthProvider>
        <LoginPage />
      </AuthProvider>
    </MemoryRouter>,
  )
}

describe('LoginPage', () => {
  beforeEach(() => {
    mockPost.mockReset()
  })

  it('envia e-mail e senha para POST /auth/login ao submeter o formulário', async () => {
    // 1ª chamada: refresh silencioso do AuthProvider ao montar (sem sessão -> falha).
    // 2ª chamada: o submit do formulário de login.
    mockPost.mockRejectedValueOnce(new Error('sem sessão')).mockResolvedValueOnce({
      data: {
        access_token: 'fake-token',
        token_type: 'bearer',
        user: { id: 1, name: 'Gestora', email: 'gestora@kijapa.com', role: 'GESTOR', store_id: 1, active: true },
      },
    })

    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('E-mail'), 'gestora@kijapa.com')
    await user.type(screen.getByLabelText('Senha'), 'SenhaForte123!')
    await user.click(screen.getByRole('button', { name: /entrar/i }))

    await waitFor(() => {
      expect(mockPost).toHaveBeenLastCalledWith('/auth/login', {
        email: 'gestora@kijapa.com',
        password: 'SenhaForte123!',
      })
    })
  })

  it('mostra mensagem de erro quando o login falha', async () => {
    mockPost.mockRejectedValueOnce(new Error('sem sessão')).mockRejectedValueOnce(new Error('credenciais inválidas'))

    const user = userEvent.setup()
    renderLoginPage()

    await user.type(screen.getByLabelText('E-mail'), 'gestora@kijapa.com')
    await user.type(screen.getByLabelText('Senha'), 'senha-errada')
    await user.click(screen.getByRole('button', { name: /entrar/i }))

    expect(await screen.findByRole('alert')).toHaveTextContent(/e-mail ou senha inválidos/i)
  })

  it('exibe a logo e os textos de identidade da marca', () => {
    mockPost.mockRejectedValueOnce(new Error('sem sessão'))

    renderLoginPage()

    expect(screen.getByRole('heading', { name: /acesse sua conta/i })).toBeInTheDocument()
    expect(screen.getByText(/a rotina da sua cozinha sob controle/i)).toBeInTheDocument()
    const logos = screen.getAllByAltText('CheckPronto')
    expect(logos.length).toBeGreaterThan(0)
    for (const logo of logos) {
      expect(logo).toHaveAttribute('src', '/logo.png')
    }
  })

  it('alterna a visibilidade da senha ao clicar no ícone do olho', async () => {
    mockPost.mockRejectedValueOnce(new Error('sem sessão'))
    const user = userEvent.setup()
    renderLoginPage()

    const passwordInput = screen.getByLabelText('Senha')
    expect(passwordInput).toHaveAttribute('type', 'password')

    await user.click(screen.getByRole('button', { name: /mostrar senha/i }))
    expect(passwordInput).toHaveAttribute('type', 'text')

    await user.click(screen.getByRole('button', { name: /ocultar senha/i }))
    expect(passwordInput).toHaveAttribute('type', 'password')
  })
})
