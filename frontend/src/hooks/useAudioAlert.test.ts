import { renderHook } from '@testing-library/react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useAudioAlert } from './useAudioAlert'

class FakeAudioContext {
  state = 'running'
  currentTime = 0
  destination = {}
  resume = vi.fn().mockResolvedValue(undefined)
  createOscillator = vi.fn(() => ({
    type: 'sine',
    frequency: { value: 0 },
    connect: vi.fn(),
    start: vi.fn(),
    stop: vi.fn(),
  }))
  createGain = vi.fn(() => ({
    gain: {
      setValueAtTime: vi.fn(),
      linearRampToValueAtTime: vi.fn(),
      exponentialRampToValueAtTime: vi.fn(),
    },
    connect: vi.fn(),
  }))
}

describe('useAudioAlert', () => {
  let originalAudioContext: typeof window.AudioContext | undefined

  beforeEach(() => {
    originalAudioContext = window.AudioContext
    // @ts-expect-error — fake mínimo só com o que o hook usa, ver classe acima.
    window.AudioContext = FakeAudioContext
  })

  afterEach(() => {
    window.AudioContext = originalAudioContext as typeof window.AudioContext
  })

  it('quando desabilitado (store_settings.enable_audio_alerts=false), não cria nenhum AudioContext', () => {
    const createSpy = vi.spyOn(window, 'AudioContext')
    const { result } = renderHook(() => useAudioAlert(false))

    result.current.playSuccess()
    result.current.playWarning()

    expect(createSpy).not.toHaveBeenCalled()
  })

  it('quando habilitado, toca o beep de sucesso sem lançar erro', () => {
    const { result } = renderHook(() => useAudioAlert(true))

    expect(() => result.current.playSuccess()).not.toThrow()
  })

  it('quando habilitado, toca o beep de aviso sem lançar erro', () => {
    const { result } = renderHook(() => useAudioAlert(true))

    expect(() => result.current.playWarning()).not.toThrow()
  })

  it('reaproveita o mesmo AudioContext entre beeps, em vez de criar um novo a cada chamada', () => {
    const createSpy = vi.spyOn(window, 'AudioContext')
    const { result } = renderHook(() => useAudioAlert(true))

    result.current.playSuccess()
    result.current.playWarning()

    expect(createSpy).toHaveBeenCalledTimes(1)
  })
})
