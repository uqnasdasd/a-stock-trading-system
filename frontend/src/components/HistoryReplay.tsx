import React, { useState, useEffect, useRef, useCallback } from 'react'

interface ReplayTick {
  time: string
  phase: string
  price: number
  volume: number
  change_pct: number
  signals: string[]
}

interface ReplayReport {
  code: string
  name: string
  date: string
  total_ticks: number
  open_price: number
  close_price: number
  high_price: number
  low_price: number
  total_volume: number
  total_amount: number
  change_pct: number
  amplitude: number
  key_signals: string[]
  phase_summary: Record<string, any>
}

const SPEEDS = [
  { label: '1x', value: 1 },
  { label: '2x', value: 2 },
  { label: '5x', value: 5 },
  { label: '10x', value: 10 },
]

const HistoryReplay: React.FC = () => {
  const [code, setCode] = useState('sh600519')
  const [date, setDate] = useState('2024-01-15')
  const [speed, setSpeed] = useState(1)
  const [ticks, setTicks] = useState<ReplayTick[]>([])
  const [currentIndex, setCurrentIndex] = useState(0)
  const [isPlaying, setIsPlaying] = useState(false)
  const [report, setReport] = useState<ReplayReport | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const intervalRef = useRef<ReturnType<typeof setInterval> | null>(null)
  const canvasRef = useRef<HTMLCanvasElement>(null)

  const loadData = useCallback(async () => {
    setLoading(true)
    setError('')
    try {
      const res = await fetch('/api/history/replay/load', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, date, speed }),
      })
      const json = await res.json()
      if (json.success) {
        setTicks(json.ticks || [])
        setCurrentIndex(0)
        setReport(json.report || null)
      } else {
        setError(json.message || '加载失败')
      }
    } catch (e: any) {
      setError(e.message || '加载失败')
    } finally {
      setLoading(false)
    }
  }, [code, date, speed])

  const generateReport = useCallback(async () => {
    try {
      const res = await fetch('/api/history/replay/report', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code, date }),
      })
      const json = await res.json()
      if (json.report) {
        setReport(json.report)
      }
    } catch (e) {
      console.error('生成报告失败:', e)
    }
  }, [code, date])

  // 回放结束时自动生成报告
  useEffect(() => {
    if (ticks.length > 0 && currentIndex === ticks.length - 1 && !report) {
      generateReport()
    }
  }, [currentIndex, ticks.length, report, generateReport])

  useEffect(() => {
    if (isPlaying && currentIndex < ticks.length - 1) {
      intervalRef.current = setInterval(() => {
        setCurrentIndex(prev => {
          if (prev >= ticks.length - 1) {
            setIsPlaying(false)
            return prev
          }
          return prev + 1
        })
      }, 600 / speed)
    } else {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
        intervalRef.current = null
      }
    }
    return () => {
      if (intervalRef.current) {
        clearInterval(intervalRef.current)
      }
    }
  }, [isPlaying, currentIndex, ticks.length, speed])

  const drawChart = useCallback(() => {
    if (!ticks.length || !canvasRef.current) return
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

    const prices = ticks.map(t => t.price)
    const minPrice = Math.min(...prices) * 0.998
    const maxPrice = Math.max(...prices) * 1.002
    const priceRange = maxPrice - minPrice || 1

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
      const val = maxPrice - (priceRange / 4) * i
      ctx.fillStyle = '#5A6B87'
      ctx.font = '10px monospace'
      ctx.textAlign = 'right'
      ctx.fillText(val.toFixed(2), padding.left - 6, y + 3)
    }

    // Price line
    const step = chartW / (ticks.length - 1 || 1)
    ctx.strokeStyle = '#00D4AA'
    ctx.lineWidth = 1.5
    ctx.beginPath()
    ticks.forEach((tick, i) => {
      const x = padding.left + i * step
      const y = padding.top + ((maxPrice - tick.price) / priceRange) * chartH
      if (i === 0) ctx.moveTo(x, y)
      else ctx.lineTo(x, y)
    })
    ctx.stroke()

    // Current position marker
    if (currentIndex >= 0 && currentIndex < ticks.length) {
      const cx = padding.left + currentIndex * step
      const cy = padding.top + ((maxPrice - ticks[currentIndex].price) / priceRange) * chartH
      ctx.fillStyle = '#FFB84D'
      ctx.beginPath()
      ctx.arc(cx, cy, 4, 0, Math.PI * 2)
      ctx.fill()
    }

    // X labels
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    const xStep = Math.ceil(ticks.length / 6)
    for (let i = 0; i < ticks.length; i += xStep) {
      const x = padding.left + i * step
      ctx.fillText(ticks[i].time.slice(0, 5), x, height - 8)
    }

    // Title
    ctx.fillStyle = '#E8ECF4'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(`历史回放 - ${code} ${date}`, padding.left, padding.top - 6)
  }, [ticks, currentIndex, code, date])

  useEffect(() => {
    drawChart()
  }, [drawChart])

  const currentTick = ticks[currentIndex]

  const phaseLabel = (phase: string) => {
    switch (phase) {
      case 'auction': return '竞价'
      case 'open': return '开盘'
      case 'intraday': return '盘中'
      case 'close': return '尾盘'
      default: return phase
    }
  }

  const exportReport = useCallback(() => {
    if (!report) return
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `replay_report_${report.code}_${report.date}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [report])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>历史回放</h3>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* 控制面板 */}
      <div style={styles.controlCard}>
        <div style={styles.controlRow}>
          <div style={styles.controlItem}>
            <label style={styles.controlLabel}>股票代码</label>
            <input
              style={styles.controlInput}
              value={code}
              onChange={e => setCode(e.target.value)}
              placeholder="如: sh600519"
            />
          </div>
          <div style={styles.controlItem}>
            <label style={styles.controlLabel}>日期</label>
            <input
              style={styles.controlInput}
              type="date"
              value={date}
              onChange={e => setDate(e.target.value)}
            />
          </div>
          <div style={styles.controlItem}>
            <label style={styles.controlLabel}>倍速</label>
            <div style={styles.speedGroup}>
              {SPEEDS.map(s => (
                <button
                  key={s.value}
                  style={{
                    ...styles.speedBtn,
                    ...(speed === s.value ? styles.speedBtnActive : {}),
                  }}
                  onClick={() => setSpeed(s.value)}
                >
                  {s.label}
                </button>
              ))}
            </div>
          </div>
          <button style={styles.loadBtn} onClick={loadData} disabled={loading}>
            {loading ? '加载中...' : '加载数据'}
          </button>
        </div>

        {ticks.length > 0 && (
          <div style={styles.playbackRow}>
            <button
              style={styles.playBtn}
              onClick={() => setIsPlaying(!isPlaying)}
            >
              {isPlaying ? '暂停' : '播放'}
            </button>
            <button
              style={styles.stopBtn}
              onClick={() => {
                setIsPlaying(false)
                setCurrentIndex(0)
              }}
            >
              停止
            </button>
            <div style={styles.progressBar}>
              <div
                style={{
                  ...styles.progressFill,
                  width: `${ticks.length > 0 ? (currentIndex / (ticks.length - 1)) * 100 : 0}%`,
                }}
              />
            </div>
            <span style={styles.progressText}>
              {currentIndex + 1} / {ticks.length}
            </span>
          </div>
        )}
      </div>

      {/* 当前行情 */}
      {currentTick && (
        <div style={styles.tickCard}>
          <div style={styles.tickGrid}>
            <div style={styles.tickItem}>
              <div style={styles.tickLabel}>时间</div>
              <div style={styles.tickValue}>{currentTick.time}</div>
            </div>
            <div style={styles.tickItem}>
              <div style={styles.tickLabel}>阶段</div>
              <div style={styles.tickValue}>{phaseLabel(currentTick.phase)}</div>
            </div>
            <div style={styles.tickItem}>
              <div style={styles.tickLabel}>价格</div>
              <div style={{ ...styles.tickValue, color: currentTick.change_pct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                ¥{currentTick.price.toFixed(2)}
              </div>
            </div>
            <div style={styles.tickItem}>
              <div style={styles.tickLabel}>涨跌幅</div>
              <div style={{ ...styles.tickValue, color: currentTick.change_pct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {currentTick.change_pct >= 0 ? '+' : ''}{currentTick.change_pct.toFixed(2)}%
              </div>
            </div>
            <div style={styles.tickItem}>
              <div style={styles.tickLabel}>成交量</div>
              <div style={styles.tickValue}>{currentTick.volume.toLocaleString()}</div>
            </div>
          </div>
          {currentTick.signals.length > 0 && (
            <div style={styles.signalsRow}>
              {currentTick.signals.map((sig, idx) => (
                <span key={idx} style={styles.signalBadge}>{sig}</span>
              ))}
            </div>
          )}
        </div>
      )}

      {/* 行情图 */}
      {ticks.length > 0 && (
        <div style={styles.chartCard}>
          <canvas ref={canvasRef} style={styles.canvas} />
        </div>
      )}

      {/* 复盘报告 */}
      {report && (
        <div style={styles.reportCard}>
          <div style={styles.reportHeader}>
            <div style={styles.reportTitle}>复盘报告</div>
            <button style={styles.exportBtn} onClick={exportReport}>导出报告</button>
          </div>
          <div style={styles.reportGrid}>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>开盘价</div>
              <div style={styles.reportValue}>¥{report.open_price.toFixed(2)}</div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>收盘价</div>
              <div style={styles.reportValue}>¥{report.close_price.toFixed(2)}</div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>最高价</div>
              <div style={styles.reportValue}>¥{report.high_price.toFixed(2)}</div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>最低价</div>
              <div style={styles.reportValue}>¥{report.low_price.toFixed(2)}</div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>涨跌幅</div>
              <div style={{ ...styles.reportValue, color: report.change_pct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {report.change_pct >= 0 ? '+' : ''}{report.change_pct.toFixed(2)}%
              </div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>振幅</div>
              <div style={styles.reportValue}>{report.amplitude.toFixed(2)}%</div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>总成交量</div>
              <div style={styles.reportValue}>{report.total_volume.toLocaleString()}</div>
            </div>
            <div style={styles.reportItem}>
              <div style={styles.reportLabel}>总成交额</div>
              <div style={styles.reportValue}>¥{report.total_amount.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</div>
            </div>
          </div>
          {report.key_signals.length > 0 && (
            <div style={styles.signalsRow}>
              <span style={{ color: '#7A8BA7', fontSize: '12px', marginRight: '8px' }}>关键信号:</span>
              {report.key_signals.map((sig, idx) => (
                <span key={idx} style={styles.signalBadge}>{sig}</span>
              ))}
            </div>
          )}
          {Object.keys(report.phase_summary).length > 0 && (
            <div style={styles.phaseSummary}>
              <div style={{ color: '#7A8BA7', fontSize: '12px', marginBottom: '8px' }}>阶段统计</div>
              <div style={styles.phaseGrid}>
                {Object.entries(report.phase_summary).map(([phase, data]: [string, any]) => (
                  <div key={phase} style={styles.phaseCard}>
                    <div style={styles.phaseName}>{phaseLabel(phase)}</div>
                    <div style={styles.phaseStat}>Ticks: {data.tick_count}</div>
                    <div style={styles.phaseStat}>成交量: {data.volume?.toLocaleString()}</div>
                    <div style={styles.phaseStat}>价格变化: {data.price_change >= 0 ? '+' : ''}{data.price_change?.toFixed(2)}</div>
                  </div>
                ))}
              </div>
            </div>
          )}
        </div>
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
  },
  title: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  error: {
    padding: '10px 12px',
    background: 'rgba(255,107,107,0.15)',
    border: '1px solid rgba(255,107,107,0.3)',
    borderRadius: '6px',
    color: '#FF6B6B',
    fontSize: '13px',
  },
  controlCard: {
    padding: '14px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  controlRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '12px',
    alignItems: 'flex-end',
  },
  controlItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    flex: '1 1 140px',
  },
  controlLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
  },
  controlInput: {
    padding: '6px 10px',
    background: '#0B1120',
    border: '1px solid #243050',
    borderRadius: '4px',
    color: '#E8ECF4',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'inherit',
  },
  speedGroup: {
    display: 'flex',
    gap: '4px',
  },
  speedBtn: {
    padding: '4px 10px',
    border: '1px solid #243050',
    borderRadius: '4px',
    background: '#0B1120',
    color: '#7A8BA7',
    fontSize: '12px',
    cursor: 'pointer',
  },
  speedBtnActive: {
    background: '#00D4AA',
    color: '#0B1120',
    borderColor: '#00D4AA',
    fontWeight: 600,
  },
  loadBtn: {
    padding: '6px 16px',
    border: 'none',
    borderRadius: '6px',
    background: '#00D4AA',
    color: '#0B1120',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  playbackRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    paddingTop: '8px',
    borderTop: '1px solid #243050',
  },
  playBtn: {
    padding: '4px 14px',
    border: 'none',
    borderRadius: '4px',
    background: '#00D4AA',
    color: '#0B1120',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  stopBtn: {
    padding: '4px 14px',
    border: '1px solid #FF6B6B',
    borderRadius: '4px',
    background: 'transparent',
    color: '#FF6B6B',
    fontSize: '13px',
    cursor: 'pointer',
  },
  progressBar: {
    flex: 1,
    height: '6px',
    background: '#0B1120',
    borderRadius: '3px',
    overflow: 'hidden',
  },
  progressFill: {
    height: '100%',
    background: '#00D4AA',
    borderRadius: '3px',
    transition: 'width 0.1s linear',
  },
  progressText: {
    fontSize: '12px',
    color: '#7A8BA7',
    fontFamily: 'monospace',
    minWidth: '60px',
    textAlign: 'right',
  },
  tickCard: {
    padding: '14px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  tickGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(100px, 1fr))',
    gap: '10px',
  },
  tickItem: {
    textAlign: 'center',
  },
  tickLabel: {
    fontSize: '11px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  tickValue: {
    fontSize: '16px',
    fontWeight: 700,
    fontFamily: 'monospace',
    color: '#E8ECF4',
  },
  signalsRow: {
    display: 'flex',
    flexWrap: 'wrap',
    gap: '6px',
    marginTop: '10px',
    paddingTop: '10px',
    borderTop: '1px solid #243050',
    alignItems: 'center',
  },
  signalBadge: {
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '11px',
    fontWeight: 600,
    background: 'rgba(0,212,170,0.15)',
    color: '#00D4AA',
    border: '1px solid rgba(0,212,170,0.3)',
  },
  chartCard: {
    background: '#131B2E',
    borderRadius: '8px',
    border: '1px solid #243050',
    padding: '12px',
  },
  canvas: {
    width: '100%',
    height: '240px',
    display: 'block',
  },
  reportCard: {
    padding: '14px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  reportHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  reportTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
  },
  exportBtn: {
    padding: '4px 12px',
    border: '1px solid #5A6B87',
    borderRadius: '4px',
    background: 'transparent',
    color: '#5A6B87',
    fontSize: '12px',
    cursor: 'pointer',
  },
  reportGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(120px, 1fr))',
    gap: '10px',
    marginBottom: '12px',
  },
  reportItem: {
    textAlign: 'center',
    padding: '8px',
    background: '#131B2E',
    borderRadius: '6px',
  },
  reportLabel: {
    fontSize: '11px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  reportValue: {
    fontSize: '15px',
    fontWeight: 700,
    fontFamily: 'monospace',
    color: '#E8ECF4',
  },
  phaseSummary: {
    marginTop: '12px',
    paddingTop: '12px',
    borderTop: '1px solid #243050',
  },
  phaseGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
    gap: '8px',
  },
  phaseCard: {
    padding: '10px',
    background: '#131B2E',
    borderRadius: '6px',
  },
  phaseName: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#00D4AA',
    marginBottom: '6px',
  },
  phaseStat: {
    fontSize: '11px',
    color: '#7A8BA7',
    lineHeight: '1.6',
  },
}

export default HistoryReplay
