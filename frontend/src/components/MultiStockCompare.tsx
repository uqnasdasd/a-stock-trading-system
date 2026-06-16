import React, { useState, useEffect, useRef, useCallback } from 'react'

interface StockInfo {
  code: string
  name: string
  price: number
  change_pct: number
  open: number
  high: number
  low: number
  pre_close: number
  kline: { day: string; open: number; high: number; low: number; close: number }[]
}

const MultiStockCompare: React.FC = () => {
  const [codes, setCodes] = useState<string[]>([])
  const [input, setInput] = useState('')
  const [stocks, setStocks] = useState<StockInfo[]>([])
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  const fetchStocks = useCallback(async () => {
    if (codes.length === 0) return
    setLoading(true)
    try {
      const results: StockInfo[] = []
      for (const code of codes) {
        const res = await fetch(`/api/stock/search?code=${code}`)
        const json = await res.json()
        if (json.found) {
          const klineRes = await fetch(`/api/stock/kline?code=${code}&scale=240&datalen=30`)
          const klineJson = await klineRes.json()
          results.push({
            code: json.code,
            name: json.name,
            price: json.price,
            change_pct: json.change_pct,
            open: json.open,
            high: json.high,
            low: json.low,
            pre_close: json.pre_close,
            kline: klineJson.data || [],
          })
        }
      }
      setStocks(results)
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    } catch (e) {
      console.error('多股对比获取失败:', e)
    } finally {
      setLoading(false)
    }
  }, [codes])

  useEffect(() => {
    fetchStocks()
    const timer = setInterval(fetchStocks, 5000)
    return () => clearInterval(timer)
  }, [fetchStocks])

  const addStock = () => {
    if (!input.trim()) return
    if (codes.length >= 4) {
      alert('最多支持4只股票对比')
      return
    }
    const code = input.trim()
    if (!codes.includes(code)) {
      setCodes(prev => [...prev, code])
    }
    setInput('')
  }

  const removeStock = (code: string) => {
    setCodes(prev => prev.filter(c => c !== code))
    setStocks(prev => prev.filter(s => s.code !== code))
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>多股同列对比</h3>
        <div style={styles.headerRight}>
          {loading && <span style={styles.loadingDot}>刷新中</span>}
          {lastUpdate && <span style={styles.lastUpdate}>{lastUpdate}</span>}
        </div>
      </div>

      <div style={styles.addRow}>
        <input
          style={styles.input}
          placeholder="输入股票代码 (最多4只)"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && addStock()}
        />
        <button style={styles.addBtn} onClick={addStock} disabled={codes.length >= 4}>
          添加
        </button>
      </div>

      {codes.length > 0 && (
        <div style={styles.tagList}>
          {codes.map(code => (
            <span key={code} style={styles.tag}>
              {code}
              <button style={styles.tagRemove} onClick={() => removeStock(code)}>x</button>
            </span>
          ))}
        </div>
      )}

      {stocks.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyText}>暂无对比股票</div>
          <div style={styles.emptySub}>添加股票代码开始对比</div>
        </div>
      ) : (
        <div style={styles.grid}>
          {stocks.map(stock => (
            <StockCard key={stock.code} stock={stock} />
          ))}
        </div>
      )}
    </div>
  )
}

const StockCard: React.FC<{ stock: StockInfo }> = ({ stock }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const color = stock.change_pct >= 0 ? '#00D4AA' : '#FF6B6B'

  useEffect(() => {
    if (!canvasRef.current || stock.kline.length === 0) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const padding = { top: 4, bottom: 4, left: 2, right: 2 }
    const chartW = width - padding.left - padding.right
    const chartH = height - padding.top - padding.bottom

    const prices = stock.kline.flatMap(d => [d.high, d.low])
    const maxPrice = Math.max(...prices) * 1.01
    const minPrice = Math.min(...prices) * 0.99
    const range = maxPrice - minPrice || 1

    const gap = chartW / stock.kline.length
    const candleW = Math.max(1, gap * 0.6)

    ctx.clearRect(0, 0, width, height)

    stock.kline.forEach((d, i) => {
      const x = padding.left + i * gap + gap / 2
      const yOpen = padding.top + ((maxPrice - d.open) / range) * chartH
      const yClose = padding.top + ((maxPrice - d.close) / range) * chartH
      const yHigh = padding.top + ((maxPrice - d.high) / range) * chartH
      const yLow = padding.top + ((maxPrice - d.low) / range) * chartH

      const isUp = d.close >= d.open
      const c = isUp ? '#00D4AA' : '#FF6B6B'

      ctx.strokeStyle = c
      ctx.fillStyle = c
      ctx.lineWidth = 1

      ctx.beginPath()
      ctx.moveTo(x, yHigh)
      ctx.lineTo(x, yLow)
      ctx.stroke()

      const bodyTop = Math.min(yOpen, yClose)
      const bodyH = Math.max(Math.abs(yClose - yOpen), 1)
      ctx.fillRect(x - candleW / 2, bodyTop, candleW, bodyH)
    })
  }, [stock])

  return (
    <div style={styles.card}>
      <div style={styles.cardHeader}>
        <div>
          <span style={styles.cardName}>{stock.name}</span>
          <span style={styles.cardCode}>{stock.code}</span>
        </div>
        <div style={{ textAlign: 'right' }}>
          <div style={{ ...styles.cardPrice, color }}>{stock.price.toFixed(2)}</div>
          <div style={{ ...styles.cardChange, color }}>
            {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
          </div>
        </div>
      </div>
      <div style={styles.cardDetail}>
        <span>开: {stock.open.toFixed(2)}</span>
        <span>高: {stock.high.toFixed(2)}</span>
        <span>低: {stock.low.toFixed(2)}</span>
      </div>
      <canvas ref={canvasRef} style={styles.miniCanvas} />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  title: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
  },
  loadingDot: {
    fontSize: '11px',
    color: '#FFB84D',
  },
  lastUpdate: {
    fontSize: '11px',
    color: '#5A6B87',
    fontFamily: 'monospace',
  },
  addRow: {
    display: 'flex',
    gap: '8px',
  },
  input: {
    flex: 1,
    padding: '8px 12px',
    background: '#1A2540',
    border: '1px solid #243050',
    borderRadius: '6px',
    color: '#E8ECF4',
    fontSize: '14px',
    outline: 'none',
  },
  addBtn: {
    padding: '8px 16px',
    background: '#00D4AA',
    color: '#0B1120',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  tagList: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  tag: {
    display: 'inline-flex',
    alignItems: 'center',
    gap: '4px',
    padding: '4px 10px',
    background: '#1A2540',
    border: '1px solid #243050',
    borderRadius: '4px',
    fontSize: '13px',
    color: '#E8ECF4',
    fontFamily: 'monospace',
  },
  tagRemove: {
    background: 'none',
    border: 'none',
    color: '#FF6B6B',
    cursor: 'pointer',
    fontSize: '14px',
    padding: '0 2px',
  },
  empty: {
    padding: '40px 20px',
    textAlign: 'center',
  },
  emptyText: {
    fontSize: '14px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  emptySub: {
    fontSize: '12px',
    color: '#5A6B87',
  },
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '12px',
  },
  card: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'flex-start',
    marginBottom: '8px',
  },
  cardName: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#E8ECF4',
    marginRight: '6px',
  },
  cardCode: {
    fontSize: '11px',
    color: '#7A8BA7',
    fontFamily: 'monospace',
  },
  cardPrice: {
    fontSize: '18px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  cardChange: {
    fontSize: '13px',
    fontWeight: 600,
    fontFamily: 'monospace',
  },
  cardDetail: {
    display: 'flex',
    gap: '12px',
    fontSize: '11px',
    color: '#7A8BA7',
    marginBottom: '8px',
    fontFamily: 'monospace',
  },
  miniCanvas: {
    width: '100%',
    height: '100px',
    display: 'block',
    background: '#131B2E',
    borderRadius: '4px',
  },
}

export default MultiStockCompare
