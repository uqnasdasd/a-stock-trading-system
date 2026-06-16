import { useState, useEffect, useRef, useCallback } from 'react'
import { useAlertSound } from './useAlertSound'

interface MarketData {
  indices?: any[]
  auction?: any
  positions?: any
  signals?: any[]
  risk?: any
  limit?: any
  timestamp?: string
}

export function useMarketData() {
  const [data, setData] = useState<MarketData | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const [isLoading, setIsLoading] = useState(true)
  const wsRef = useRef<WebSocket | null>(null)
  const pollRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)
  const prevSignalsRef = useRef<Set<string>>(new Set())

  // 声音告警
  const { playAlert } = useAlertSound()

  // 检测新信号并触发声音告警
  const checkNewSignals = useCallback((signals: any[]) => {
    if (!signals || signals.length === 0) return

    const currentIds = new Set<string>()
    signals.forEach((signal: any) => {
      currentIds.add(signal.id)

      // 如果是新信号（之前不存在）
      if (!prevSignalsRef.current.has(signal.id)) {
        // 根据信号类型触发不同声音
        if (signal.type === 'stop_loss' || signal.type === 'position_sell') {
          playAlert('stop_loss', signal.code)
        } else if (signal.type === 'take_profit') {
          playAlert('take_profit', signal.code)
        } else if (signal.type === 'risk_alert') {
          playAlert('risk_alert', signal.code)
        } else if (signal.level === 'emergency') {
          // 紧急信号根据内容判断
          const msg = (signal.message || '').toLowerCase()
          if (msg.includes('涨停') || msg.includes('封板')) {
            playAlert('limit_up', signal.code)
          } else if (msg.includes('跌停') || msg.includes('破板')) {
            playAlert('limit_down', signal.code)
          } else {
            playAlert('risk_alert', signal.code)
          }
        }
      }
    })

    prevSignalsRef.current = currentIds
  }, [playAlert])

  // HTTP轮询获取数据 - 优化：避免重复请求，减少闪烁
  const isFetchingRef = useRef(false)
  const fetchData = useCallback(async () => {
    if (isFetchingRef.current) return
    isFetchingRef.current = true
    try {
      setIsLoading(true)
      const [indicesRes, riskRes, positionsRes, signalsRes, auctionRes, limitRes] = await Promise.all([
        fetch(`/api/market/indices`).then(r => r.json()).catch(() => null),
        fetch(`/api/risk/status`).then(r => r.json()).catch(() => null),
        fetch(`/api/positions`).then(r => r.json()).catch(() => null),
        fetch(`/api/signals`).then(r => r.json()).catch(() => null),
        fetch(`/api/auction/analyze`).then(r => r.json()).catch(() => null),
        fetch(`/api/limit/stocks`).then(r => r.json()).catch(() => null),
      ])

      const newSignals = signalsRes?.signals || []
      checkNewSignals(newSignals)

      setData(prev => {
        // 只在数据真正变化时更新，避免不必要的重渲染
        const next = {
          ...prev,
          indices: indicesRes?.indices || prev?.indices,
          risk: riskRes?.status || prev?.risk,
          positions: positionsRes || prev?.positions,
          signals: newSignals,
          auction: auctionRes || prev?.auction,
          limit: limitRes || prev?.limit,
          timestamp: new Date().toISOString(),
        }
        return next
      })
      setIsConnected(true)
    } catch (e) {
      console.error('Fetch error:', e)
      setIsConnected(false)
    } finally {
      setIsLoading(false)
      isFetchingRef.current = false
    }
  }, [checkNewSignals])

  // WebSocket连接
  const connectWS = useCallback(() => {
    try {
      const wsProtocol = window.location.protocol === 'https:' ? 'wss:' : 'ws:'
      const wsHost = window.location.host
      const ws = new WebSocket(`${wsProtocol}//${wsHost}/ws`)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        ws.send(JSON.stringify({ action: 'subscribe_market' }))
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          if (msg.type === 'market_update') {
            // 检查是否有新信号
            if (msg.signals && msg.signals.length > 0) {
              checkNewSignals(msg.signals)
            }
            setData(prev => ({ ...prev, ...msg }))
          }
        } catch (e) {
          console.error('Parse error:', e)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        reconnectRef.current = setTimeout(connectWS, 5000)
      }

      ws.onerror = () => {
        setIsConnected(false)
      }
    } catch (e) {
      reconnectRef.current = setTimeout(connectWS, 5000)
    }
  }, [checkNewSignals])

  useEffect(() => {
    // 立即获取一次数据
    fetchData()
    // 每3秒轮询
    pollRef.current = setInterval(fetchData, 3000)
    // 同时尝试WebSocket
    connectWS()

    return () => {
      if (pollRef.current) clearInterval(pollRef.current)
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [fetchData, connectWS])

  const refresh = useCallback(() => {
    fetchData()
  }, [fetchData])

  return { data, isConnected, isLoading, refresh }
}
