import { act, renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { formatMMSS, isTaskOverdue, slaProgressPercent, useTaskTimer } from './useTaskTimer'

describe('useTaskTimer', () => {
  beforeEach(() => {
    vi.useFakeTimers()
  })

  afterEach(() => {
    vi.useRealTimers()
  })

  it('formata os segundos iniciais como MM:SS', () => {
    const { result } = renderHook(() => useTaskTimer(65))

    expect(result.current).toBe('01:05')
  })

  it('avança um segundo por vez, sozinho, entre atualizações do servidor', () => {
    const { result } = renderHook(() => useTaskTimer(0))

    expect(result.current).toBe('00:00')

    act(() => {
      vi.advanceTimersByTime(3000)
    })

    expect(result.current).toBe('00:03')
  })

  it('resincroniza com o valor do servidor quando ele muda (refetch)', () => {
    const { result, rerender } = renderHook(({ elapsed }) => useTaskTimer(elapsed), {
      initialProps: { elapsed: 10 },
    })

    act(() => {
      vi.advanceTimersByTime(2000)
    })
    expect(result.current).toBe('00:12')

    // O backend respondeu de novo (refetch de 5s) com um valor mais preciso —
    // o hook precisa adotar esse valor, não continuar contando do seu próprio.
    rerender({ elapsed: 20 })
    expect(result.current).toBe('00:20')
  })

  it('não conta tempo quando ainda não há elapsed_seconds (tarefa não iniciada)', () => {
    const { result } = renderHook(() => useTaskTimer(null))

    act(() => {
      vi.advanceTimersByTime(5000)
    })

    expect(result.current).toBe('00:00')
  })
})

describe('isTaskOverdue', () => {
  it('nunca é "com atraso" quando a tarefa não tem SLA configurado', () => {
    expect(isTaskOverdue(999999, null)).toBe(false)
  })

  it('não é "com atraso" enquanto o tempo corrido está dentro do SLA', () => {
    expect(isTaskOverdue(5 * 60, 10)).toBe(false)
  })

  it('não é "com atraso" exatamente no limite do SLA (só depois de ultrapassar)', () => {
    expect(isTaskOverdue(10 * 60, 10)).toBe(false)
  })

  it('é "com atraso" assim que o tempo corrido ultrapassa o SLA', () => {
    expect(isTaskOverdue(10 * 60 + 1, 10)).toBe(true)
  })
})

describe('formatMMSS', () => {
  it('formata minutos e segundos com dois dígitos', () => {
    expect(formatMMSS(0)).toBe('00:00')
    expect(formatMMSS(65)).toBe('01:05')
    expect(formatMMSS(10 * 60)).toBe('10:00')
  })
})

describe('slaProgressPercent', () => {
  it('é nulo quando a tarefa não tem SLA configurado', () => {
    expect(slaProgressPercent(300, null)).toBeNull()
  })

  it('calcula o percentual do SLA já consumido', () => {
    expect(slaProgressPercent(5 * 60, 10)).toBe(50)
    expect(slaProgressPercent(10 * 60, 10)).toBe(100)
  })

  it('passa de 100 quando o tempo corrido ultrapassa o SLA (atraso)', () => {
    expect(slaProgressPercent(15 * 60, 10)).toBe(150)
  })
})
