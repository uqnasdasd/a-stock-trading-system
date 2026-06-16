import { useState, useEffect, useRef, useCallback } from 'react'

interface WSData {
  type: string
  indices?: any[]
  auction?: any
  positions?: any
  signals?: any[]
  risk?: any
  [key: string]: any
}

export function useWebSocket(url: string) {
  const [data, setData] = useState<WSData | null>(null)
  const [isConnected, setIsConnected] = useState(false)
  const wsRef = useRef<WebSocket | null>(null)
  const reconnectRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  const connect = useCallback(() => {
    try {
      const ws = new WebSocket(url)
      wsRef.current = ws

      ws.onopen = () => {
        console.log('WebSocket connected')
        setIsConnected(true)
        // 订阅市场行情
        ws.send(JSON.stringify({ action: 'subscribe_market' }))
      }

      ws.onmessage = (event) => {
        try {
          const msg = JSON.parse(event.data)
          setData(msg)
        } catch (e) {
          console.error('Parse error:', e)
        }
      }

      ws.onclose = () => {
        console.log('WebSocket disconnected')
        setIsConnected(false)
        // 自动重连
        reconnectRef.current = setTimeout(connect, 3000)
      }

      ws.onerror = (error) => {
        console.error('WebSocket error:', error)
      }
    } catch (e) {
      console.error('Connection error:', e)
      reconnectRef.current = setTimeout(connect, 3000)
    }
  }, [url])

  useEffect(() => {
    connect()
    return () => {
      if (reconnectRef.current) clearTimeout(reconnectRef.current)
      wsRef.current?.close()
    }
  }, [connect])

  const send = useCallback((msg: object) => {
    if (wsRef.current?.readyState === WebSocket.OPEN) {
      wsRef.current.send(JSON.stringify(msg))
    }
  }, [])

  return { data, isConnected, send }
}
