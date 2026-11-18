import { useCallback, useRef } from 'react'

type BeepKind = 'success' | 'warning'

const FREQUENCY_HZ: Record<BeepKind, number> = {
  success: 880,
  warning: 440,
}

interface WebkitWindow {
  webkitAudioContext?: typeof AudioContext
}

export function useAudioAlert(enabled: boolean) {
  const audioContextRef = useRef<AudioContext | null>(null)

  const play = useCallback(
    (kind: BeepKind) => {
      if (!enabled) return

      const AudioContextClass = window.AudioContext ?? (window as unknown as WebkitWindow).webkitAudioContext
      if (!AudioContextClass) return

      if (!audioContextRef.current) {
        audioContextRef.current = new AudioContextClass()
      }
      const context = audioContextRef.current
      if (context.state === 'suspended') {
        void context.resume()
      }

      const oscillator = context.createOscillator()
      const gain = context.createGain()
      oscillator.type = 'sine'
      oscillator.frequency.value = FREQUENCY_HZ[kind]

      // Envelope curto (subida rápida, queda suave) — soa como um "beep" de
      // notificação, não um alarme contínuo.
      const now = context.currentTime
      gain.gain.setValueAtTime(0, now)
      gain.gain.linearRampToValueAtTime(0.2, now + 0.02)
      gain.gain.exponentialRampToValueAtTime(0.0001, now + 0.3)

      oscillator.connect(gain)
      gain.connect(context.destination)
      oscillator.start(now)
      oscillator.stop(now + 0.3)
    },
    [enabled],
  )

  return {
    playSuccess: () => play('success'),
    playWarning: () => play('warning'),
  }
}
