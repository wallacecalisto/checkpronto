import { useEffect, useState } from 'react'

export function formatMMSS(totalSeconds: number): string {
  const minutes = Math.floor(totalSeconds / 60)
  const seconds = totalSeconds % 60
  return `${String(minutes).padStart(2, '0')}:${String(seconds).padStart(2, '0')}`
}

export function isTaskOverdue(elapsedSeconds: number, estimatedDurationMinutes: number | null): boolean {
  if (estimatedDurationMinutes === null) return false
  return elapsedSeconds > estimatedDurationMinutes * 60
}

export function slaProgressPercent(elapsedSeconds: number, estimatedDurationMinutes: number | null): number | null {
  if (estimatedDurationMinutes === null || estimatedDurationMinutes <= 0) return null
  return (elapsedSeconds / (estimatedDurationMinutes * 60)) * 100
}

export function useTaskTimer(elapsedSeconds: number | null): string {
  const [displaySeconds, setDisplaySeconds] = useState(elapsedSeconds ?? 0)

  useEffect(() => {
    setDisplaySeconds(elapsedSeconds ?? 0)
  }, [elapsedSeconds])

  useEffect(() => {
    if (elapsedSeconds === null) return

    const interval = setInterval(() => {
      setDisplaySeconds((current) => current + 1)
    }, 1000)

    return () => clearInterval(interval)
  }, [elapsedSeconds])

  return formatMMSS(displaySeconds)
}
