import { useState } from 'react'
import { toISODateString } from '../utils/dateTime'

export type DatePreset = 'hoje' | '7dias' | 'mes' | 'personalizado'

// Calcula o intervalo de um preset fixo — "personalizado" não passa por
// aqui (é controlado pelos campos de data do próprio hook).
export function computePresetRange(preset: 'hoje' | '7dias' | 'mes'): { from: string; to: string } {
  const now = new Date()
  const to = toISODateString(now)

  if (preset === 'hoje') return { from: to, to }

  if (preset === '7dias') {
    const from = new Date(now)
    from.setDate(from.getDate() - 6)
    return { from: toISODateString(from), to }
  }

  // "Este mês": do dia 1 até hoje (não até o fim do mês — não faz sentido
  // filtrar por dias futuros, que nunca teriam registro nenhum).
  const from = new Date(now.getFullYear(), now.getMonth(), 1)
  return { from: toISODateString(from), to }
}

export function useDateRangeFilter(defaultPreset: 'hoje' | '7dias' | 'mes' = '7dias') {
  const [preset, setPreset] = useState<DatePreset>(defaultPreset)
  const defaultRange = computePresetRange(defaultPreset)
  const [customFrom, setCustomFrom] = useState(defaultRange.from)
  const [customTo, setCustomTo] = useState(defaultRange.to)

  function selectPreset(nextPreset: DatePreset): void {
    // Ao entrar em "Personalizado", pré-preenche os campos com o intervalo
    // que estava sendo exibido — menos surpreendente do que abrir em branco.
    if (nextPreset === 'personalizado' && preset !== 'personalizado') {
      const current = computePresetRange(preset)
      setCustomFrom(current.from)
      setCustomTo(current.to)
    }
    setPreset(nextPreset)
  }

  const { from, to } = preset === 'personalizado' ? { from: customFrom, to: customTo } : computePresetRange(preset)

  return { preset, selectPreset, customFrom, setCustomFrom, customTo, setCustomTo, from, to }
}
