interface NumpadProps {
  value: string
  maxLength: number
  onChange: (value: string) => void
  disabled?: boolean
}

const DIGITS = ['1', '2', '3', '4', '5', '6', '7', '8', '9'] as const

export function Numpad({ value, maxLength, onChange, disabled = false }: NumpadProps) {
  function pressDigit(digit: string): void {
    if (disabled || value.length >= maxLength) return
    onChange(value + digit)
  }

  function pressBackspace(): void {
    if (disabled || value.length === 0) return
    onChange(value.slice(0, -1))
  }

  return (
    <div className="flex flex-col items-center gap-6">
      {/* verde reservado para sucesso — dígitos e progresso do PIN
          são entrada neutra, não uma confirmação de nada, daí o índigo. */}
      <div className="flex gap-3" aria-hidden="true">
        {Array.from({ length: maxLength }, (_, index) => (
          <span
            key={index}
            className={`h-4 w-4 rounded-full border-2 transition-colors ${
              index < value.length ? 'border-indigo-500 bg-indigo-500' : 'border-slate-300'
            }`}
          />
        ))}
      </div>

      <div className="grid grid-cols-3 gap-3">
        {DIGITS.map((digit) => (
          <button
            key={digit}
            type="button"
            onClick={() => pressDigit(digit)}
            disabled={disabled}
            className="h-16 w-16 rounded-2xl bg-indigo-500 text-2xl font-semibold text-white shadow-sm transition hover:bg-indigo-600 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 sm:h-20 sm:w-20"
          >
            {digit}
          </button>
        ))}

        <button
          type="button"
          onClick={pressBackspace}
          disabled={disabled}
          className="h-16 w-16 rounded-2xl border border-slate-200 bg-slate-100 text-sm font-semibold text-slate-600 transition hover:bg-slate-200 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 sm:h-20 sm:w-20"
        >
          Apagar
        </button>

        <button
          type="button"
          onClick={() => pressDigit('0')}
          disabled={disabled}
          className="h-16 w-16 rounded-2xl bg-indigo-500 text-2xl font-semibold text-white shadow-sm transition hover:bg-indigo-600 active:scale-95 disabled:cursor-not-allowed disabled:opacity-50 sm:h-20 sm:w-20"
        >
          0
        </button>

        <span aria-hidden="true" />
      </div>
    </div>
  )
}
