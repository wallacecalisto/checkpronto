export function formatDateTimeBR(isoString: string): string {
  const date = new Date(isoString)

  const datePart = new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'America/Sao_Paulo',
  }).format(date)

  const timePart = new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  }).format(date)

  return `${datePart} às ${timePart}`
}

// Só a hora (sem data) — ex.: "14:32". Usado no Radar Ao Vivo do painel, que
// só mostra eventos de hoje — repetir a data ali seria ruído.
export function formatTimeBR(isoString: string): string {
  return new Intl.DateTimeFormat('pt-BR', {
    hour: '2-digit',
    minute: '2-digit',
    timeZone: 'America/Sao_Paulo',
  }).format(new Date(isoString))
}

// Só a data (sem hora) — ex.: "11/09/2026". Mesmo fuso do Brasil, para não
// mostrar uma data "errada" perto da virada da meia-noite em UTC.
export function formatDateBR(isoString: string): string {
  const date = new Date(isoString)

  return new Intl.DateTimeFormat('pt-BR', {
    day: '2-digit',
    month: '2-digit',
    year: 'numeric',
    timeZone: 'America/Sao_Paulo',
  }).format(date)
}

// "2026-09-11" — formato aceito pelo backend (`started_from`/`started_to`,
// filtro de data em GET /checklists) e por <input type="date">.
export function toISODateString(date: Date): string {
  const year = date.getFullYear()
  const month = String(date.getMonth() + 1).padStart(2, '0')
  const day = String(date.getDate()).padStart(2, '0')
  return `${year}-${month}-${day}`
}

export function formatDurationShort(totalSeconds: number): string {
  const totalMinutes = Math.round(totalSeconds / 60)
  const hours = Math.floor(totalMinutes / 60)
  const minutes = totalMinutes % 60
  if (hours === 0) return `${minutes}min`
  if (minutes === 0) return `${hours}h`
  return `${hours}h ${minutes}min`
}
