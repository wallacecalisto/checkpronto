import type { DatePreset } from '../../hooks/useDateRangeFilter'
import { toISODateString } from '../../utils/dateTime'

const PRESET_LABEL: Record<DatePreset, string> = {
  hoje: 'Hoje',
  '7dias': 'Últimos 7 dias',
  mes: 'Este mês',
  personalizado: 'Personalizado',
}

const PRESETS: DatePreset[] = ['hoje', '7dias', 'mes', 'personalizado']

interface DateRangePresetFilterProps {
  preset: DatePreset
  onPresetChange: (preset: DatePreset) => void
  customFrom: string
  customTo: string
  onCustomFromChange: (value: string) => void
  onCustomToChange: (value: string) => void
}

export function DateRangePresetFilter({
  preset,
  onPresetChange,
  customFrom,
  customTo,
  onCustomFromChange,
  onCustomToChange,
}: DateRangePresetFilterProps) {
  return (
    <div className="flex flex-wrap items-center gap-3">
      <div className="inline-flex flex-wrap gap-1 rounded-full border border-gray-200 bg-white p-1 shadow-sm">
        {PRESETS.map((option) => (
          <button
            key={option}
            type="button"
            onClick={() => onPresetChange(option)}
            className={`rounded-full px-3.5 py-1.5 text-sm font-medium transition ${
              preset === option ? 'bg-emerald-500 text-white shadow-sm' : 'text-gray-600 hover:bg-gray-100'
            }`}
          >
            {PRESET_LABEL[option]}
          </button>
        ))}
      </div>

      {preset === 'personalizado' && (
        <div className="flex flex-wrap items-center gap-2">
          <label className="flex items-center gap-1.5 text-sm text-gray-600">
            De
            <input
              type="date"
              value={customFrom}
              max={customTo}
              onChange={(event) => onCustomFromChange(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </label>
          <label className="flex items-center gap-1.5 text-sm text-gray-600">
            Até
            <input
              type="date"
              value={customTo}
              min={customFrom}
              max={toISODateString(new Date())}
              onChange={(event) => onCustomToChange(event.target.value)}
              className="rounded-lg border border-gray-200 bg-gray-50 px-2.5 py-1.5 text-sm text-gray-900 outline-none focus:border-emerald-500 focus:ring-2 focus:ring-emerald-500/20"
            />
          </label>
        </div>
      )}
    </div>
  )
}
