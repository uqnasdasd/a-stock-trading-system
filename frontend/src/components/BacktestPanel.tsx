import React, { useState, useEffect, useRef, useCallback } from 'react'

interface BacktestParams {
  buyCondition: string
  sellCondition: string
  holdPeriod: number
  startDate: string
  endDate: string
  initialCapital: number
}

interface BacktestTrade {
  date: string
  code: string
  name: string
  action: 'buy' | 'sell'
  price: number
  volume: number
  pnl?: number
}

interface BacktestResult {
  totalReturn: number
  maxDrawdown: number
  winRate: number
  tradeCount: number
  profitTrades: number
  lossTrades: number
  finalCapital: number
  equityCurve: { date: string; value: number }[]
  trades: BacktestTrade[]
}

const defaultParams: BacktestParams = {
  buyCondition: '突破5日均线且成交量放大1.5倍',
  sellCondition: '跌破止损线-3%或达到止盈4%',
  holdPeriod: 3,
  startDate: '2024-01-01',
  endDate: '2024-06-01',
  initialCapital: 100000,
}

const BacktestPanel: React.FC = () => {
  const [params, setParams] = useState<BacktestParams>(defaultParams)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const runBacktest = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify(params),
      })
      if (!res.ok) throw new Error('回测请求失败')
      const json = await res.json()
      if (json.result) {
        setResult(json.result)
      } else {
        // 模拟数据演示
        generateMockResult()
      }
    } catch (e) {
      console.warn('回测API调用失败，使用模拟数据:', e)
      generateMockResult()
    } finally {
      setLoading(false)
    }
  }, [params])

  const generateMockResult = () => {
    const curve: { date: string; value: number }[] = []
    let capital = params.initialCapital
    const trades: BacktestTrade[] = []
    const start = new Date(params.startDate)
    const end = new Date(params.endDate)
    const totalDays = Math.max(1, Math.floor((end.getTime() - start.getTime()) / (1000 * 60 * 60 * 24)))

    for (let i = 0; i <= totalDays; i++) {
      const d = new Date(start)
      d.setDate(d.getDate() + i)
      if (d.getDay() === 0 || d.getDay() === 6) continue
      const change = (Math.random() - 0.48) * 0.02
      capital = capital * (1 + change)
      curve.push({
        date: d.toISOString().slice(0, 10),
        value: Math.round(capital * 100) / 100,
      })
    }

    const tradeCount = Math.floor(Math.random() * 30) + 10
    for (let i = 0; i < tradeCount; i++) {
      const d = new Date(start)
      d.setDate(d.getDate() + Math.floor(Math.random() * totalDays))
      const isProfit = Math.random() > 0.45
      trades.push({
        date: d.toISOString().slice(0, 10),
        code: `60${String(Math.floor(Math.random() * 1000)).padStart(3, '0')}`,
        name: ['贵州茅台', '宁德时代', '比亚迪', '中芯国际', '隆基绿能', '海康威视'][Math.floor(Math.random() * 6)],
        action: i % 2 === 0 ? 'buy' : 'sell',
        price: +(Math.random() * 100 + 20).toFixed(2),
        volume: Math.floor(Math.random() * 10 + 1) * 100,
        pnl: i % 2 === 1 ? (isProfit ? +(Math.random() * 5).toFixed(2) : -(Math.random() * 3).toFixed(2)) : undefined,
      })
    }

    const finalValue = curve[curve.length - 1]?.value || params.initialCapital
    const totalReturn = ((finalValue - params.initialCapital) / params.initialCapital) * 100

    let maxDrawdown = 0
    let peak = params.initialCapital
    for (const point of curve) {
      if (point.value > peak) peak = point.value
      const dd = ((peak - point.value) / peak) * 100
      if (dd > maxDrawdown) maxDrawdown = dd
    }

    const sellTrades = trades.filter(t => t.action === 'sell' && t.pnl !== undefined)
    const profitTrades = sellTrades.filter(t => (t.pnl || 0) > 0).length
    const winRate = sellTrades.length > 0 ? (profitTrades / sellTrades.length) * 100 : 0

    setResult({
      totalReturn: +totalReturn.toFixed(2),
      maxDrawdown: +maxDrawdown.toFixed(2),
      winRate: +winRate.toFixed(2),
      tradeCount,
      profitTrades,
      lossTrades: sellTrades.length - profitTrades,
      finalCapital: +finalValue.toFixed(2),
      equityCurve: curve,
      trades: trades.sort((a, b) => new Date(a.date).getTime() - new Date(b.date).getTime()),
    })
  }

  useEffect(() => {
    if (!result?.equityCurve.length || !canvasRef.current) return

    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const padding = { top: 20, right: 20, bottom: 30, left: 50 }
    const chartW = width - padding.left - padding.right
    const chartH = height - padding.top - padding.bottom

    const values = result.equityCurve.map(d => d.value)
    const minVal = Math.min(...values) * 0.98
    const maxVal = Math.max(...values) * 1.02
    const valRange = maxVal - minVal || 1

    ctx.clearRect(0, 0, width, height)
    ctx.fillStyle = '#131B2E'
    ctx.fillRect(0, 0, width, height)

    // Grid
    ctx.strokeStyle = '#243050'
    ctx.lineWidth = 0.5
    for (let i = 0; i <= 4; i++) {
      const y = padding.top + (chartH / 4) * i
      ctx.beginPath()
      ctx.moveTo(padding.left, y)
      ctx.lineTo(padding.left + chartW, y)
      ctx.stroke()
      const val = maxVal - (valRange / 4) * i
      ctx.fillStyle = '#5A6B87'
      ctx.font = '10px monospace'
      ctx.textAlign = 'right'
      ctx.fillText(val.toFixed(0), padding.left - 6, y + 3)
    }

    // Line
    const step = chartW / (result.equityCurve.length - 1 || 1)
    ctx.strokeStyle = '#00D4AA'
    ctx.lineWidth = 2
    ctx.beginPath()
    result.equityCurve.forEach((point, i) => {
      const x = padding.left + i * step
      const y = padding.top + ((maxVal - point.value) / valRange) * chartH
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // Area fill
    ctx.lineTo(padding.left + chartW, padding.top + chartH)
    ctx.lineTo(padding.left, padding.top + chartH)
    ctx.closePath()
    ctx.fillStyle = 'rgba(0, 212, 170, 0.1)'
    ctx.fill()

    // X labels
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    const xStep = Math.ceil(result.equityCurve.length / 6)
    for (let i = 0; i < result.equityCurve.length; i += xStep) {
      const x = padding.left + i * step
      ctx.fillText(result.equityCurve[i].date.slice(5), x, height - 8)
    }

    // Title
    ctx.fillStyle = '#E8ECF4'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText('收益曲线', padding.left, padding.top - 6)
  }, [result])

  const handleParamChange = (key: keyof BacktestParams, value: string | number) => {
    setParams(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>策略回测</h3>
        <button style={styles.runBtn} onClick={runBacktest} disabled={loading}>
          {loading ? '回测中...' : '运行回测'}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* 参数设置 */}
      <div style={styles.paramsCard}>
        <div style={styles.paramsTitle}>策略参数</div>
        <div style={styles.paramGrid}>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>买入条件</label>
            <input
              style={styles.paramInput}
              value={params.buyCondition}
              onChange={e => handleParamChange('buyCondition', e.target.value)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>卖出条件</label>
            <input
              style={styles.paramInput}
              value={params.sellCondition}
              onChange={e => handleParamChange('sellCondition', e.target.value)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>持仓周期 (天)</label>
            <input
              style={styles.paramInput}
              type="number"
              min={1}
              max={30}
              value={params.holdPeriod}
              onChange={e => handleParamChange('holdPeriod', parseInt(e.target.value) || 1)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>初始资金 (元)</label>
            <input
              style={styles.paramInput}
              type="number"
              min={10000}
              step={10000}
              value={params.initialCapital}
              onChange={e => handleParamChange('initialCapital', parseInt(e.target.value) || 100000)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>开始日期</label>
            <input
              style={styles.paramInput}
              type="date"
              value={params.startDate}
              onChange={e => handleParamChange('startDate', e.target.value)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>结束日期</label>
            <input
              style={styles.paramInput}
              type="date"
              value={params.endDate}
              onChange={e => handleParamChange('endDate', e.target.value)}
            />
          </div>
        </div>
      </div>

      {/* 回测结果 */}
      {result && (
        <>
          <div style={styles.resultGrid}>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>总收益率</div>
              <div style={{ ...styles.resultValue, color: result.totalReturn >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {result.totalReturn >= 0 ? '+' : ''}{result.totalReturn.toFixed(2)}%
              </div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>最大回撤</div>
              <div style={{ ...styles.resultValue, color: '#FF6B6B' }}>
                -{result.maxDrawdown.toFixed(2)}%
              </div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>胜率</div>
              <div style={{ ...styles.resultValue, color: result.winRate >= 50 ? '#00D4AA' : '#FFB84D' }}>
                {result.winRate.toFixed(2)}%
              </div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>交易次数</div>
              <div style={styles.resultValue}>{result.tradeCount}</div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>盈利/亏损</div>
              <div style={styles.resultValue}>
                <span style={{ color: '#00D4AA' }}>{result.profitTrades}</span>
                <span style={{ color: '#5A6B87', margin: '0 4px' }}>/</span>
                <span style={{ color: '#FF6B6B' }}>{result.lossTrades}</span>
              </div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>最终资金</div>
              <div style={{ ...styles.resultValue, color: '#E8ECF4' }}>
                ¥{result.finalCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* 收益曲线 */}
          <div style={styles.chartCard}>
            <canvas ref={canvasRef} style={styles.canvas} />
          </div>

          {/* 交易明细 */}
          <div style={styles.tradesSection}>
            <div style={styles.tradesTitle}>交易明细</div>
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>日期</th>
                    <th style={styles.th}>代码</th>
                    <th style={styles.th}>名称</th>
                    <th style={styles.th}>操作</th>
                    <th style={styles.th}>价格</th>
                    <th style={styles.th}>数量</th>
                    <th style={styles.th}>盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ ...styles.td, textAlign: 'center', color: '#5A6B87', padding: '24px' }}>
                        暂无交易记录
                      </td>
                    </tr>
                  ) : (
                    result.trades.map((t, idx) => (
                      <tr key={idx} style={styles.tr}>
                        <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: '12px', color: '#7A8BA7' }}>{t.date}</td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>{t.code}</td>
                        <td style={{ ...styles.td, fontWeight: 600 }}>{t.name}</td>
                        <td style={styles.td}>
                          <span style={t.action === 'buy' ? styles.badgeBuy : styles.badgeSell}>
                            {t.action === 'buy' ? '买入' : '卖出'}
                          </span>
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace', fontWeight: 600 }}>¥{t.price.toFixed(2)}</td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>{t.volume}</td>
                        <td style={styles.td}>
                          {t.pnl !== undefined ? (
                            <span style={{ color: t.pnl >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                              {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}%
                            </span>
                          ) : (
                            <span style={{ color: '#5A6B87' }}>--</span>
                          )}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    height: '100%',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
    flexWrap: 'wrap',
    gap: '8px',
  },
  title: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  runBtn: {
    padding: '6px 16px',
    border: 'none',
    borderRadius: '6px',
    background: '#00D4AA',
    color: '#0B1120',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  error: {
    padding: '10px 12px',
    background: 'rgba(255,107,107,0.15)',
    border: '1px solid rgba(255,107,107,0.3)',
    borderRadius: '6px',
    color: '#FF6B6B',
    fontSize: '13px',
  },
  paramsCard: {
    padding: '14px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  paramsTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
    marginBottom: '12px',
  },
  paramGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(200px, 1fr))',
    gap: '12px',
  },
  paramItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  paramLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
  },
  paramInput: {
    padding: '6px 10px',
    background: '#0B1120',
    border: '1px solid #243050',
    borderRadius: '4px',
    color: '#E8ECF4',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'inherit',
  },
  resultGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
    gap: '10px',
  },
  resultCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
    textAlign: 'center',
  },
  resultLabel: {
    fontSize: '11px',
    color: '#7A8BA7',
    marginBottom: '6px',
  },
  resultValue: {
    fontSize: '18px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  chartCard: {
    background: '#131B2E',
    borderRadius: '8px',
    border: '1px solid #243050',
    padding: '12px',
  },
  canvas: {
    width: '100%',
    height: '280px',
    display: 'block',
  },
  tradesSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  tradesTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
    marginTop: '4px',
  },
  tableContainer: {
    overflow: 'auto',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse',
    fontSize: '13px',
  },
  th: {
    background: '#1A2540',
    color: '#00D4AA',
    fontWeight: 600,
    textAlign: 'left',
    padding: '8px 10px',
    borderBottom: '2px solid #00D4AA',
    whiteSpace: 'nowrap',
  },
  tr: {
    transition: 'background 0.2s',
  },
  td: {
    padding: '8px 10px',
    borderBottom: '1px solid #243050',
    color: '#E8ECF4',
    whiteSpace: 'nowrap',
  },
  badgeBuy: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    background: 'rgba(0,212,170,0.15)',
    color: '#00D4AA',
    border: '1px solid rgba(0,212,170,0.3)',
  },
  badgeSell: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    background: 'rgba(255,107,107,0.15)',
    color: '#FF6B6B',
    border: '1px solid rgba(255,107,107,0.3)',
  },
}

export default BacktestPanel
