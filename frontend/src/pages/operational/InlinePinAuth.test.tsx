import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { beforeEach, describe, expect, it, vi } from 'vitest'
import { InlinePinAuth, type InlinePinAuthPerson } from './InlinePinAuth'

const mockSetupPin = vi.fn()

vi.mock('../../services/employeeService', () => ({
  setupPin: (...args: unknown[]) => mockSetupPin(...args),
}))

const carlos: InlinePinAuthPerson = { id: 7, name: 'Carlos Ajudante', hasPin: true }
const bruna: InlinePinAuthPerson = { id: 8, name: 'Bruna', hasPin: true }
const semPin: InlinePinAuthPerson = { id: 9, name: 'Novato', hasPin: false }

function renderAuth(
  people: InlinePinAuthPerson[],
  onAuthenticate: (person: InlinePinAuthPerson, pin: string) => Promise<void>,
  onSuccess = vi.fn(),
  onCancel = vi.fn(),
) {
  const queryClient = new QueryClient()
  render(
    <QueryClientProvider client={queryClient}>
      <InlinePinAuth title="Quem vai iniciar?" people={people} onAuthenticate={onAuthenticate} onSuccess={onSuccess} onCancel={onCancel} />
    </QueryClientProvider>,
  )
  return { onSuccess, onCancel }
}

async function typePin(user: ReturnType<typeof userEvent.setup>, pin: string) {
  for (const digit of pin) {
    await user.click(screen.getByRole('button', { name: digit }))
  }
}

describe('InlinePinAuth', () => {
  beforeEach(() => {
    mockSetupPin.mockReset()
  })

  it('lista as pessoas, pede o PIN de quem foi escolhido, e chama onAuthenticate + onSuccess', async () => {
    const onAuthenticate = vi.fn().mockResolvedValue(undefined)
    const user = userEvent.setup()
    const { onSuccess } = renderAuth([carlos, bruna], onAuthenticate)

    expect(screen.getByText('Carlos Ajudante')).toBeInTheDocument()
    expect(screen.getByText('Bruna')).toBeInTheDocument()

    await user.click(screen.getByText('Carlos Ajudante'))
    expect(screen.getByText(/digite o pin de/i)).toBeInTheDocument()
    await typePin(user, '1234')

    await waitFor(() => expect(onAuthenticate).toHaveBeenCalledWith(carlos, '1234'))
    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
  })

  it('mostra "Sem PIN" para quem ainda não tem PIN cadastrado', () => {
    renderAuth([semPin], vi.fn())

    expect(screen.getByText('Sem PIN')).toBeInTheDocument()
  })

  it('mostra o KeyIcon ao lado do nome, sem remover o texto "Sem PIN"', () => {
    renderAuth([semPin], vi.fn())

    const nameButton = screen.getByRole('button', { name: /Novato/ })
    expect(nameButton.querySelector('svg[aria-hidden="true"]')).not.toBeNull()
    expect(screen.getByText('Novato')).toBeInTheDocument()
    expect(screen.getByText('Sem PIN')).toBeInTheDocument()
  })

  it('PIN_NOT_SET entra no fluxo de criar PIN e tenta a ação de novo com o PIN criado', async () => {
    const onAuthenticate = vi
      .fn()
      .mockRejectedValueOnce({ isAxiosError: true, response: { data: { detail: 'sem pin', code: 'PIN_NOT_SET' } } })
      .mockResolvedValueOnce(undefined)
    mockSetupPin.mockResolvedValueOnce({ employee_id: carlos.id, name: carlos.name })
    const user = userEvent.setup()
    const { onSuccess } = renderAuth([carlos], onAuthenticate)

    await user.click(screen.getByText('Carlos Ajudante'))
    await typePin(user, '1234')

    expect(await screen.findByText(/ainda não tem um pin/i)).toBeInTheDocument()
    await typePin(user, '5678')
    expect(await screen.findByText(/digite o mesmo pin de novo/i)).toBeInTheDocument()
    await typePin(user, '5678')

    await waitFor(() => expect(mockSetupPin).toHaveBeenCalledWith(carlos.id, '5678'))
    await waitFor(() => expect(onAuthenticate).toHaveBeenLastCalledWith(carlos, '5678'))
    await waitFor(() => expect(onSuccess).toHaveBeenCalled())
  })

  it('PINs diferentes na confirmação mostram erro e voltam pro início da criação', async () => {
    const onAuthenticate = vi
      .fn()
      .mockRejectedValueOnce({ isAxiosError: true, response: { data: { detail: 'sem pin', code: 'PIN_NOT_SET' } } })
    const user = userEvent.setup()
    renderAuth([carlos], onAuthenticate)

    await user.click(screen.getByText('Carlos Ajudante'))
    await typePin(user, '1234')
    await screen.findByText(/ainda não tem um pin/i)
    await typePin(user, '1111')
    await typePin(user, '2222')

    expect(await screen.findByRole('alert')).toHaveTextContent(/não conferem/i)
    expect(mockSetupPin).not.toHaveBeenCalled()
  })

  it('PIN incorreto mostra "PIN incorreto." e permite tentar de novo', async () => {
    const onAuthenticate = vi
      .fn()
      .mockRejectedValueOnce({ isAxiosError: true, response: { data: { detail: 'PIN incorreto.', code: 'PIN_INCORRECT' } } })
    const user = userEvent.setup()
    renderAuth([carlos], onAuthenticate)

    await user.click(screen.getByText('Carlos Ajudante'))
    await typePin(user, '0000')

    expect(await screen.findByRole('alert')).toHaveTextContent('PIN incorreto.')
    // continua na tela de PIN (não volta pra lista) — pode tentar de novo.
    expect(screen.getByText(/digite o pin de/i)).toBeInTheDocument()
  })

  it('PIN bloqueado trava o numpad', async () => {
    const onAuthenticate = vi.fn().mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'bloqueado', code: 'PIN_LOCKED', locked_until: '2026-09-25T10:00:00Z' } },
    })
    const user = userEvent.setup()
    renderAuth([carlos], onAuthenticate)

    await user.click(screen.getByText('Carlos Ajudante'))
    await typePin(user, '0000')

    expect(await screen.findByRole('alert')).toHaveTextContent(/pin bloqueado/i)
    expect(screen.getByRole('button', { name: '1' })).toBeDisabled()
  })

  it('erro de negócio (ex.: já tem tarefa ativa) mostra a mensagem real e volta pra escolha de pessoa', async () => {
    const onAuthenticate = vi.fn().mockRejectedValueOnce({
      isAxiosError: true,
      response: { data: { detail: 'Você já tem uma tarefa em andamento.', code: 'EMPLOYEE_HAS_ACTIVE_TASK' } },
    })
    const user = userEvent.setup()
    renderAuth([carlos, bruna], onAuthenticate)

    await user.click(screen.getByText('Carlos Ajudante'))
    await typePin(user, '1234')

    expect(await screen.findByRole('alert')).toHaveTextContent(/já tem uma tarefa em andamento/i)
    // voltou pra lista de pessoas (não travado na tela de PIN de quem falhou).
    expect(screen.getByText('Bruna')).toBeInTheDocument()
  })

  it('"Não é você? Escolher outro nome" volta pra lista sem chamar a ação', async () => {
    const onAuthenticate = vi.fn()
    const user = userEvent.setup()
    renderAuth([carlos, bruna], onAuthenticate)

    await user.click(screen.getByText('Carlos Ajudante'))
    await user.click(screen.getByText(/escolher outro nome/i))

    expect(screen.getByText('Bruna')).toBeInTheDocument()
    expect(onAuthenticate).not.toHaveBeenCalled()
  })

  it('cancelar fecha sem chamar a ação', async () => {
    const onAuthenticate = vi.fn()
    const user = userEvent.setup()
    const { onCancel } = renderAuth([carlos], onAuthenticate)

    await user.click(screen.getByRole('button', { name: 'Fechar' }))

    expect(onCancel).toHaveBeenCalled()
    expect(onAuthenticate).not.toHaveBeenCalled()
  })

  it('mostra mensagem quando não há ninguém pra escolher', () => {
    renderAuth([], vi.fn())

    expect(screen.getByText('Nenhum funcionário ativo neste setor.')).toBeInTheDocument()
  })
})
