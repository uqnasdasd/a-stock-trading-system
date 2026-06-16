import React, { useRef, useEffect, useState } from 'react'

interface MinuteData {
  time: string
  price: number
  avg_price: number
  volume: number
}

interface Props {
  code: string
  name: string
}

const MinuteChart: React.FC<Props> = ({ code, name }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<MinuteData[]>([])
  const [loading, setLoading] = useState(false)
  const [stats, setStats] = useState({
    current: 0,
    changePct: 0,
    high: 0,
    low: 0,
    preClose: 0,
  })

  const fetchMinute = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/stock/minute?code=${code}`)
      const json = await res.json()
      if (json.data && json.data.length > 0) {
        setData(json.data)
        const prices = json.data.map((d: MinuteData) => d.price)
        const preClose = json.pre_close || prices[0]
        const current = prices[prices.length - 1]
        const high = Math.max(...prices)
        const low = Math.min(...prices)
        const changePct = preClose ? ((current - preClose) / preClose) * 100 : 0
        setStats({ current, changePct, high, low, preClose })
      }
    } catch (e) {
      console.error('分时数据获取失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchMinute()
    const timer = setInterval(fetchMinute, 30000)
    return () => clearInterval(timer)
  }, [code])

  useEffect(() => {
    if (!data.length || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const padding = { top: 20, right: 60, bottom: 30, left: 10 }
    const volumeRatio = 0.25
    const chartW = width - padding.left - padding.right
    const totalH = height - padding.top - padding.bottom
    const priceH = totalH * (1 - volumeRatio)
    const volumeH = totalH * volumeRatio
    const volumeTop = padding.top + priceH + 8

    const prices = data.map(d => d.price)
    const avgPrices = data.map(d => d.avg_price).filter(v => v > 0)
    const preClose = stats.preClose || prices[0]

    const maxPrice = Math.max(...prices, ...avgPrices, preClose * 1.02)
    const minPrice = Math.min(...prices, ...avgPrices, preClose * 0.98)
    const priceRange = maxPrice - minPrice || 1

    const volumes = data.map(d => d.volume)
    const maxVolume = Math.max(...volumes, 1)

    // 背景
    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#131B2E'
    ctx.fillRect(0, 0, width, height)

    // 网格线
    ctx.strokeStyle = '#243050'
    ctx.lineWidth = 0.5
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (priceH / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartW, y)
      ctx.stroke()

      const price = maxPrice - (priceRange / 5) * i
      const pct = ((price - preClose) / preClose) * 100
      ctx.fillStyle = pct >= 0 ? '#00D4AA' : '#FF6B6B'
      ctx.font = '10px monospace'
      ctx.textAlign = 'left'
      ctx.fillText(price.toFixed(2), padding.left + chartW + 4, y + 3)
      ctx.fillStyle = pct >= 0 ? 'rgba(0,212,170,0.6)' : 'rgba(255,107,107,0.6)'
      ctx.fillText(`${pct >= 0 ? '+' : ''}${pct.toFixed(2)}%`, padding.left + chartW + 4, y + 14)
    }

    // 昨收线
    const yPreClose = padding.top + ((maxPrice - preClose) / priceRange) * priceH
    ctx.strokeStyle = 'rgba(122,139,167,0.4)'
    ctx.setLineDash([4, 4])
    ctx.beginPath()
    ctx.moveTo(padding.left, yPreClose)
    ctx.lineTo(padding.left + chartW, yPreClose)
    ctx.stroke()
    ctx.setLineDash([])

    // 成交量分隔线
    ctx.strokeStyle = '#243050'
    ctx.beginPath()
    ctx.moveTo(padding.left, volumeTop - 4)
    ctx.lineTo(padding.left + chartW, volumeTop - 4)
    ctx.stroke()

    // 成交量网格
    for (let i = 0; i <= 2; i++) {
      const y = volumeTop + (volumeH / 2) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartW, y)
      ctx.stroke()
    }

    const gap = chartW / data.length

    // 绘制成交量
    data.forEach((d, i) => {
      const x = padding.left + i * gap + gap / 2
      const volBarH = (d.volume / maxVolume) * volumeH
      const volBarTop = volumeTop + volumeH - volBarH
      const isUp = d.price >= preClose
      ctx.fillStyle = isUp ? 'rgba(0,212,170,0.5)' : 'rgba(255,107,107,0.5)'
      const barW = Math.max(1, gap * 0.6)
      ctx.fillRect(x - barW / 2, volBarTop, barW, volBarH)
    })

    // 绘制均价线
    ctx.strokeStyle = '#FFD700'
    ctx.lineWidth = 1.2
    ctx.beginPath()
    let avgStarted = false
    data.forEach((d, i) => {
      if (d.avg_price <= 0) return
      const x = padding.left + i * gap + gap / 2
      const y = padding.top + ((maxPrice - d.avg_price) / priceRange) * priceH
      if (!avgStarted) {
        ctx.moveTo(x, y)
        avgStarted = true
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // 绘制价格线
    ctx.strokeStyle = '#FFFFFF'
    ctx.lineWidth = 1.2
    ctx.beginPath()
    data.forEach((d, i) => {
      const x = padding.left + i * gap + gap / 2
      const y = padding.top + ((maxPrice - d.price) / priceRange) * priceH
      if (i === 0) {
        ctx.moveTo(x, y)
      } else {
        ctx.lineTo(x, y)
      }
    })
    ctx.stroke()

    // 当前价格点
    const lastIdx = data.length - 1
    const lastX = padding.left + lastIdx * gap + gap / 2
    const lastY = padding.top + ((maxPrice - data[lastIdx].price) / priceRange) * priceH
    ctx.fillStyle = '#FFFFFF'
    ctx.beginPath()
    ctx.arc(lastX, lastY, 3, 0, Math.PI * 2)
    ctx.fill()

    // 时间标签
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    const timeStep = Math.ceil(data.length / 6)
    for (let i = 0; i < data.length; i += timeStep) {
      const x = padding.left + i * gap + gap / 2
      ctx.fillText(data[i].time.slice(0, 5), x, height - 10)
    }

    // 标题
    ctx.fillStyle = '#E8ECF4'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(`${name} (${code}) 分时走势`, padding.left, padding.top - 6)

    // 图例
    const legendX = padding.left + 200
    ctx.font = '10px monospace'
    ctx.fillStyle = '#FFFFFF'
    ctx.fillText('价格', legendX, padding.top - 6)
    ctx.fillStyle = '#FFD700'
    ctx.fillText('均价', legendX + 40, padding.top - 6)
  }, [data, stats, name, code])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <div style={styles.stats}>
          <span style={styles.statItem}>
            现价: <span style={{ color: stats.changePct >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 700 }}>
              {stats.current.toFixed(2)}
            </span>
          </span>
          <span style={styles.statItem}>
            涨跌: <span style={{ color: stats.changePct >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 700 }}>
              {stats.changePct >= 0 ? '+' : ''}{stats.changePct.toFixed(2)}%
            </span>
          </span>
          <span style={styles.statItem}>
            最高: <span style={{ color: '#00D4AA' }}>{stats.high.toFixed(2)}</span>
          </span>
          <span style={styles.statItem}>
            最低: <span style={{ color: '#FF6B6B' }}>{stats.low.toFixed(2)}</span>
          </span>
        </div>
        <button style={styles.refreshBtn} onClick={fetchMinute} disabled={loading}>
          {loading ? '刷新中...' : '刷新'}
        </button>
      </div>
      <canvas ref={canvasRef} style={styles.canvas} />
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    background: '#131B2E',
    borderRadius: '8px',
    border: '1px solid #243050',
    padding: '12px',
    marginTop: '12px',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  stats: {
    display: 'flex',
    gap: '16px',
    flexWrap: 'wrap',
  },
  statItem: {
    fontSize: '13px',
    color: '#7A8BA7',
    fontFamily: 'monospace',
  },
  refreshBtn: {
    padding: '4px 12px',
    border: 'none',
    borderRadius: '4px',
    background: '#243050',
    color: '#E8ECF4',
    fontSize: '12px',
    cursor: 'pointer',
  },
  canvas: {
    width: '100%',
    height: '320px',
    display: 'block',
  },
}

export default MinuteChart
