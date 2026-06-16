import React, { useRef, useEffect, useState } from 'react'

interface KlineData {
  day: string
  open: number
  high: number
  low: number
  close: number
  volume: number
}

interface Props {
  code: string
  name: string
}

/**
 * 计算移动均线
 * MA(N) = 最近N根K线收盘价之和 / N
 */
function calculateMA(data: KlineData[], period: number): (number | null)[] {
  const result: (number | null)[] = []
  for (let i = 0; i < data.length; i++) {
    if (i < period - 1) {
      result.push(null)
    } else {
      let sum = 0
      for (let j = i - period + 1; j <= i; j++) {
        sum += data[j].close
      }
      result.push(sum / period)
    }
  }
  return result
}

const KlineChart: React.FC<Props> = ({ code, name }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)
  const [data, setData] = useState<KlineData[]>([])
  const [scale, setScale] = useState(5)
  const [loading, setLoading] = useState(false)

  const fetchKline = async () => {
    setLoading(true)
    try {
      const res = await fetch(`/api/stock/kline?code=${code}&scale=${scale}&datalen=100`)
      const json = await res.json()
      if (json.data) {
        setData(json.data)
      }
    } catch (e) {
      console.error('K线获取失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchKline()
  }, [code, scale])

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

    // 边距
    const padding = { top: 20, right: 50, bottom: 30, left: 10 }
    // 成交量区域占比
    const volumeRatio = 0.2
    const chartW = width - padding.left - padding.right
    const totalH = height - padding.top - padding.bottom
    const klineH = totalH * (1 - volumeRatio)
    const volumeH = totalH * volumeRatio
    const volumeTop = padding.top + klineH + 8 // K线和成交量之间的间距

    // 计算价格范围
    const prices = data.flatMap(d => [d.high, d.low])
    const maxPrice = Math.max(...prices) * 1.02
    const minPrice = Math.min(...prices) * 0.98
    const priceRange = maxPrice - minPrice

    // 计算成交量范围
    const volumes = data.map(d => d.volume)
    const maxVolume = Math.max(...volumes, 1)

    // 计算均线
    const ma5 = calculateMA(data, 5)
    const ma10 = calculateMA(data, 10)
    const ma20 = calculateMA(data, 20)

    // 清空
    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#131B2E'
    ctx.fillRect(0, 0, width, height)

    // 绘制K线区域网格线
    ctx.strokeStyle = '#243050'
    ctx.lineWidth = 0.5
    for (let i = 0; i <= 5; i++) {
      const y = padding.top + (klineH / 5) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartW, y)
      ctx.stroke()

      // 价格标签
      const price = maxPrice - (priceRange / 5) * i
      ctx.fillStyle = '#5A6B87'
      ctx.font = '10px monospace'
      ctx.textAlign = 'left'
      ctx.fillText(price.toFixed(2), padding.left + chartW + 4, y + 3)
    }

    // 绘制成交量区域分隔线
    ctx.strokeStyle = '#243050'
    ctx.lineWidth = 0.5
    ctx.beginPath()
    ctx.moveTo(padding.left, volumeTop - 4)
    ctx.lineTo(padding.left + chartW, volumeTop - 4)
    ctx.stroke()

    // 绘制成交量区域网格线
    for (let i = 0; i <= 2; i++) {
      const y = volumeTop + (volumeH / 2) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartW, y)
      ctx.stroke()
    }

    // K线和成交量共用间距
    const gap = chartW / data.length
    const candleW = Math.max(2, gap * 0.7)

    // 绘制K线
    data.forEach((d, i) => {
      const x = padding.left + i * gap + gap / 2
      const yOpen = padding.top + ((maxPrice - d.open) / priceRange) * klineH
      const yClose = padding.top + ((maxPrice - d.close) / priceRange) * klineH
      const yHigh = padding.top + ((maxPrice - d.high) / priceRange) * klineH
      const yLow = padding.top + ((maxPrice - d.low) / priceRange) * klineH

      const isUp = d.close >= d.open
      const color = isUp ? '#00D4AA' : '#FF6B6B'

      ctx.strokeStyle = color
      ctx.fillStyle = color
      ctx.lineWidth = 1

      // 影线
      ctx.beginPath()
      ctx.moveTo(x, yHigh)
      ctx.lineTo(x, yLow)
      ctx.stroke()

      // 实体
      const bodyTop = Math.min(yOpen, yClose)
      const bodyH = Math.max(Math.abs(yClose - yOpen), 1)
      ctx.fillRect(x - candleW / 2, bodyTop, candleW, bodyH)

      // 绘制成交量柱状图
      const volBarH = (d.volume / maxVolume) * volumeH
      const volBarTop = volumeTop + volumeH - volBarH
      ctx.fillStyle = isUp ? 'rgba(0,212,170,0.5)' : 'rgba(255,107,107,0.5)'
      ctx.fillRect(x - candleW / 2, volBarTop, candleW, volBarH)
    })

    // 绘制均线
    const drawMA = (maData: (number | null)[], color: string) => {
      ctx.strokeStyle = color
      ctx.lineWidth = 1.2
      ctx.beginPath()
      let started = false
      for (let i = 0; i < maData.length; i++) {
        if (maData[i] === null) continue
        const x = padding.left + i * gap + gap / 2
        const y = padding.top + ((maxPrice - maData[i]!) / priceRange) * klineH
        if (!started) {
          ctx.moveTo(x, y)
          started = true
        } else {
          ctx.lineTo(x, y)
        }
      }
      ctx.stroke()
    }

    // MA5 白色, MA10 黄色, MA20 紫色
    drawMA(ma5, '#FFFFFF')
    drawMA(ma10, '#FFD700')
    drawMA(ma20, '#B266FF')

    // 均线图例
    const legendY = padding.top - 6
    const legendX = padding.left + 200
    ctx.font = '10px monospace'
    ctx.textAlign = 'left'

    ctx.fillStyle = '#FFFFFF'
    ctx.fillText('MA5', legendX, legendY)
    if (ma5[ma5.length - 1] !== null) {
      ctx.fillText(ma5[ma5.length - 1]!.toFixed(2), legendX + 30, legendY)
    }

    ctx.fillStyle = '#FFD700'
    ctx.fillText('MA10', legendX + 80, legendY)
    if (ma10[ma10.length - 1] !== null) {
      ctx.fillText(ma10[ma10.length - 1]!.toFixed(2), legendX + 115, legendY)
    }

    ctx.fillStyle = '#B266FF'
    ctx.fillText('MA20', legendX + 165, legendY)
    if (ma20[ma20.length - 1] !== null) {
      ctx.fillText(ma20[ma20.length - 1]!.toFixed(2), legendX + 200, legendY)
    }

    // 成交量标签
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'right'
    ctx.fillText('VOL', padding.left + chartW - 2, volumeTop + 10)

    // 时间标签（只显示部分）
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    const step = Math.ceil(data.length / 6)
    for (let i = 0; i < data.length; i += step) {
      const x = padding.left + i * gap + gap / 2
      const timeStr = data[i].day.split(' ')[1] || data[i].day.slice(5)
      ctx.fillText(timeStr, x, height - 10)
    }

    // 标题
    ctx.fillStyle = '#E8ECF4'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    const scaleText = scale === 1 ? '1分钟' : scale === 5 ? '5分钟' : scale === 15 ? '15分钟' : scale === 30 ? '30分钟' : scale === 60 ? '60分钟' : '日线'
    ctx.fillText(`${name} (${code}) ${scaleText}K线`, padding.left, padding.top - 6)
  }, [data, scale, name, code])

  return (
    <div style={styles.container}>
      <div style={styles.toolbar}>
        {[1, 5, 15, 30, 60, 240].map(s => (
          <button
            key={s}
            style={{ ...styles.scaleBtn, background: scale === s ? '#00D4AA' : '#1A2540', color: scale === s ? '#0B1120' : '#7A8BA7' }}
            onClick={() => setScale(s)}
          >
            {s === 240 ? '日' : s + '分'}
          </button>
        ))}
        <button style={styles.refreshBtn} onClick={fetchKline} disabled={loading}>
          {loading ? '加载中...' : '刷新'}
        </button>
      </div>
      <div style={styles.maLegend}>
        <span style={{ ...styles.maItem, color: '#FFFFFF' }}>MA5</span>
        <span style={{ ...styles.maItem, color: '#FFD700' }}>MA10</span>
        <span style={{ ...styles.maItem, color: '#B266FF' }}>MA20</span>
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
  toolbar: {
    display: 'flex',
    gap: '6px',
    marginBottom: '8px',
    flexWrap: 'wrap',
  },
  scaleBtn: {
    padding: '4px 10px',
    border: 'none',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  refreshBtn: {
    padding: '4px 12px',
    border: 'none',
    borderRadius: '4px',
    background: '#243050',
    color: '#E8ECF4',
    fontSize: '12px',
    cursor: 'pointer',
    marginLeft: 'auto',
  },
  maLegend: {
    display: 'flex',
    gap: '12px',
    marginBottom: '4px',
  },
  maItem: {
    fontSize: '11px',
    fontWeight: 600,
  },
  canvas: {
    width: '100%',
    height: '380px',
    display: 'block',
  },
}

export default KlineChart
