interface ToggleSwitchProps {
  id: string
  label: string
  checked: boolean
  onChange: (checked: boolean) => void
  // Texto de apoio (cinza, menor) explicando o que o campo faz.
  description?: string
  disabled?: boolean
}

export function ToggleSwitch({ id, label, checked, onChange, description, disabled = false }: ToggleSwitchProps) {
  return (
    <div className="flex items-start justify-between gap-4 py-3">
      <div className="flex flex-col gap-0.5">
        <label htmlFor={id} className="text-sm font-medium text-gray-800">
          {label}
        </label>
        {description && <p className="text-xs text-gray-400">{description}</p>}
      </div>
      <label
        htmlFor={id}
        className={`relative inline-flex h-6 w-11 shrink-0 items-center rounded-full transition-colors duration-200 ease-in-out ${
          checked ? 'bg-emerald-500' : 'bg-gray-200'
        } ${disabled ? 'cursor-not-allowed opacity-50' : 'cursor-pointer'}`}
      >
        <input
          id={id}
          type="checkbox"
          role="switch"
          checked={checked}
          disabled={disabled}
          onChange={(event) => onChange(event.target.checked)}
          className="sr-only"
        />
        <span
          className={`inline-block h-[18px] w-[18px] transform rounded-full bg-white shadow-sm transition-transform duration-200 ease-in-out ${
            checked ? 'translate-x-[22px]' : 'translate-x-[3px]'
          }`}
        />
      </label>
    </div>
  )
}
