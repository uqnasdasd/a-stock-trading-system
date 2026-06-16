import { useCallback, useRef } from 'react'

type AlertType = 'limit_up' | 'take_profit' | 'stop_loss' | 'limit_down' | 'risk_alert'

const audioContextRef: { current: AudioContext | null } = { current: null }

function getAudioContext(): AudioContext {
  if (!audioContextRef.current) {
    audioContextRef.current = new (window.AudioContext || (window as any).webkitAudioContext)()
  }
  return audioContextRef.current
}

/**
 * 使用 Web Audio API 生成提示音
 * 涨停/止盈：高音 (800Hz)
 * 止损/跌停：低音 (300Hz)
 * 风控告警：中低音 (500Hz)
 */
function playTone(frequency: number, duration: number = 0.3, volume: number = 0.3): void {
  try {
    const ctx = getAudioContext()
    if (ctx.state === 'suspended') {
      ctx.resume()
    }

    const oscillator = ctx.createOscillator()
    const gainNode = ctx.createGain()

    oscillator.connect(gainNode)
    gainNode.connect(ctx.destination)

    oscillator.type = 'sine'
    oscillator.frequency.setValueAtTime(frequency, ctx.currentTime)

    // 渐入渐出，避免爆音
    gainNode.gain.setValueAtTime(0, ctx.currentTime)
    gainNode.gain.linearRampToValueAtTime(volume, ctx.currentTime + 0.05)
    gainNode.gain.linearRampToValueAtTime(0, ctx.currentTime + duration)

    oscillator.start(ctx.currentTime)
    oscillator.stop(ctx.currentTime + duration)
  } catch (e) {
    console.error('音频播放失败:', e)
  }
}

function playAlertSequence(type: AlertType): void {
  switch (type) {
    case 'limit_up':
      // 涨停：高音三连音，上升感
      playTone(800, 0.15, 0.3)
      setTimeout(() => playTone(1000, 0.15, 0.3), 150)
      setTimeout(() => playTone(1200, 0.25, 0.35), 300)
      break

    case 'take_profit':
      // 止盈：高音双连音
      playTone(880, 0.2, 0.25)
      setTimeout(() => playTone(1100, 0.3, 0.3), 200)
      break

    case 'stop_loss':
      // 止损：低音双连音，下降感
      playTone(400, 0.2, 0.35)
      setTimeout(() => playTone(250, 0.35, 0.4), 200)
      break

    case 'limit_down':
      // 跌停：低沉连续音
      playTone(300, 0.25, 0.35)
      setTimeout(() => playTone(200, 0.25, 0.4), 250)
      setTimeout(() => playTone(150, 0.4, 0.4), 500)
      break

    case 'risk_alert':
      // 风控告警：急促中低音
      playTone(500, 0.1, 0.3)
      setTimeout(() => playTone(500, 0.1, 0.3), 120)
      setTimeout(() => playTone(400, 0.2, 0.35), 240)
      break

    default:
      playTone(600, 0.2, 0.2)
  }
}

export function useAlertSound() {
  const lastAlertRef = useRef<Record<string, number>>({})
  const cooldownMs = 5000 // 同类型信号5秒内不重复播放

  const playAlert = useCallback((type: AlertType, key?: string) => {
    const alertKey = key ? `${type}_${key}` : type
    const now = Date.now()
    const lastTime = lastAlertRef.current[alertKey] || 0

    if (now - lastTime < cooldownMs) {
      return // 冷却期内，不重复播放
    }

    lastAlertRef.current[alertKey] = now
    playAlertSequence(type)
  }, [])

  return { playAlert }
}

export { playAlertSequence, playTone }
