import { useEffect, useState } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { KeyIcon } from '../../components/icons/KeyIcon'
import { getApiErrorCode, getApiErrorField, getApiErrorMessage } from '../../services/apiClient'
import { setupPin } from '../../services/employeeService'
import { formatDateTimeBR } from '../../utils/dateTime'
import { Numpad } from './Numpad'

const PIN_INCORRECT_MESSAGE = 'PIN incorreto.'
const PIN_BLOCKED_MESSAGE = 'PIN bloqueado por tentativas incorretas consecutivas. Contate o seu líder.'

function buildBlockedMessage(error: unknown): string {
  const lockedUntil = getApiErrorField(error, 'locked_until')
  if (!lockedUntil) return PIN_BLOCKED_MESSAGE
  return `${PIN_BLOCKED_MESSAGE} Tente novamente após ${formatDateTimeBR(lockedUntil)}.`
}

export interface InlinePinAuthPerson {
  id: number
  name: string
  hasPin?: boolean
}

interface InlinePinAuthProps {
  // Título da tela (ex.: "Quem vai iniciar esta tarefa?").
  title: string
  people: InlinePinAuthPerson[]
  onAuthenticate: (person: InlinePinAuthPerson, pin: string) => Promise<void>
  onSuccess: () => void
  onCancel: () => void
}

type Step =
  | { kind: 'select-person' }
  | { kind: 'enter-pin'; person: InlinePinAuthPerson }
  | { kind: 'create-pin-first'; person: InlinePinAuthPerson }
  | { kind: 'create-pin-confirm'; person: InlinePinAuthPerson; firstPin: string }

export function InlinePinAuth({ title, people, onAuthenticate, onSuccess, onCancel }: InlinePinAuthProps) {
  const queryClient = useQueryClient()
  const [step, setStep] = useState<Step>({ kind: 'select-person' })
  const [pinInput, setPinInput] = useState('')
  const [errorMessage, setErrorMessage] = useState<string | null>(null)
  const [isSubmitting, setIsSubmitting] = useState(false)
  const [isBlocked, setIsBlocked] = useState(false)

  useEffect(() => {
    const previousOverflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.body.style.overflow = previousOverflow
    }
  }, [])

  async function attemptAuthenticate(person: InlinePinAuthPerson, pin: string): Promise<void> {
    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      await onAuthenticate(person, pin)
      onSuccess()
    } catch (error) {
      const code = getApiErrorCode(error)
      setPinInput('')

      if (code === 'PIN_NOT_SET') {
        setStep({ kind: 'create-pin-first', person })
      } else if (code === 'PIN_LOCKED' || code === 'EMPLOYEE_INACTIVE') {
        setIsBlocked(true)
        setErrorMessage(code === 'PIN_LOCKED' ? buildBlockedMessage(error) : getApiErrorMessage(error))
      } else if (code === 'PIN_INCORRECT') {
        setErrorMessage(PIN_INCORRECT_MESSAGE)
      } else {
        setErrorMessage(getApiErrorMessage(error))
        setStep({ kind: 'select-person' })
      }
    } finally {
      setIsSubmitting(false)
    }
  }

  async function handleCreatePinConfirmed(
    person: InlinePinAuthPerson,
    firstPin: string,
    confirmPin: string,
  ): Promise<void> {
    if (firstPin !== confirmPin) {
      setErrorMessage('Os PINs digitados não conferem. Tente de novo.')
      setStep({ kind: 'create-pin-first', person })
      setPinInput('')
      return
    }

    setErrorMessage(null)
    setIsSubmitting(true)
    try {
      await setupPin(person.id, firstPin)
      await queryClient.invalidateQueries({ queryKey: ['employees', 'active'] })
      setPinInput('')
      await attemptAuthenticate(person, firstPin)
    } catch (error) {
      setErrorMessage(getApiErrorMessage(error))
      setStep({ kind: 'select-person' })
      setPinInput('')
    } finally {
      setIsSubmitting(false)
    }
  }

  function handleNumpadChange(value: string): void {
    setPinInput(value)
    if (value.length !== 4) return

    if (step.kind === 'enter-pin') {
      void attemptAuthenticate(step.person, value)
    } else if (step.kind === 'create-pin-first') {
      setStep({ kind: 'create-pin-confirm', person: step.person, firstPin: value })
      setPinInput('')
    } else if (step.kind === 'create-pin-confirm') {
      void handleCreatePinConfirmed(step.person, step.firstPin, value)
    }
  }

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/50 p-4">
      <div className="flex max-h-[90vh] w-full max-w-sm flex-col rounded-3xl border border-slate-200 bg-white shadow-2xl">
        <div className="shrink-0 px-6 pt-6 sm:px-8 sm:pt-8">
          <div className="mb-4 flex items-center justify-between gap-3">
            <h2 className="text-lg font-semibold text-slate-800">{title}</h2>
            <button
              type="button"
              onClick={onCancel}
              aria-label="Fechar"
              className="rounded-full p-2 text-slate-400 transition hover:bg-slate-100 hover:text-slate-600"
            >
              ✕
            </button>
          </div>

          {errorMessage && (
            <p role="alert" className="mb-4 rounded-xl bg-red-50 px-4 py-2 text-sm text-red-600">
              {errorMessage}
            </p>
          )}
        </div>

        <div className="overflow-y-auto px-6 pb-6 sm:px-8 sm:pb-8">
          {step.kind === 'select-person' && (
            <>
              {people.length === 0 ? (
                <p className="text-center text-slate-500">Nenhum funcionário ativo neste setor.</p>
              ) : (
                <div className="grid grid-cols-2 gap-3">
                  {people.map((person) => (
                    <button
                      key={person.id}
                      type="button"
                      onClick={() => setStep({ kind: 'enter-pin', person })}
                      className="flex flex-col items-center justify-center gap-1.5 rounded-2xl border border-slate-200 bg-white px-3 py-5 text-center shadow-sm transition-all duration-300 ease-in-out hover:-translate-y-0.5 hover:border-indigo-200 hover:shadow-md active:scale-95"
                    >
                      <span className="flex items-center gap-1.5 font-semibold text-slate-800">
                        <KeyIcon className="h-3.5 w-3.5 shrink-0 text-slate-400" />
                        {person.name}
                      </span>
                      {person.hasPin === false && <span className="text-xs font-medium text-orange-500">Sem PIN</span>}
                    </button>
                  ))}
                </div>
              )}
            </>
          )}

          {step.kind === 'enter-pin' && (
            <div className="flex flex-col items-center gap-4">
              <p className="text-center text-slate-600">
                Digite o PIN de <span className="font-semibold text-slate-800">{step.person.name}</span>
              </p>
              <Numpad value={pinInput} maxLength={4} onChange={handleNumpadChange} disabled={isSubmitting || isBlocked} />
              <button
                type="button"
                onClick={() => {
                  setStep({ kind: 'select-person' })
                  setPinInput('')
                  setErrorMessage(null)
                }}
                className="text-sm font-medium text-slate-500 hover:text-slate-700"
              >
                Não é você? Escolher outro nome
              </button>
            </div>
          )}

          {step.kind === 'create-pin-first' && (
            <div className="flex flex-col items-center gap-4">
              <p className="text-center text-slate-600">
                <span className="font-semibold text-slate-800">{step.person.name}</span> ainda não tem um PIN. Crie um
                PIN de 4 dígitos.
              </p>
              <Numpad value={pinInput} maxLength={4} onChange={handleNumpadChange} disabled={isSubmitting} />
            </div>
          )}

          {step.kind === 'create-pin-confirm' && (
            <div className="flex flex-col items-center gap-4">
              <p className="text-center text-slate-600">Digite o mesmo PIN de novo para confirmar.</p>
              <Numpad value={pinInput} maxLength={4} onChange={handleNumpadChange} disabled={isSubmitting} />
            </div>
          )}
        </div>
      </div>
    </div>
  )
}
