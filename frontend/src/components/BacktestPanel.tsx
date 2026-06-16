import React, { useState, useEffect, useRef, useCallback } from 'react'

interface BacktestParams {
  code: string
  buyCondition: string
  sellCondition: string
  holdPeriod: number
  startDate: string
  endDate: string
  initialCapital: number
  stopLossPct: number
  takeProfitPct: number
  maPeriod: number
  volumeRatioThreshold: number
}

interface BacktestTrade {
  date: string
  code: string
  name: string
  action: 'buy' | 'sell'
  price: number
  volume: number
  pnl?: number
  pnlPct?: number
  reason?: string
}

interface BacktestResult {
  totalReturn: number
  maxDrawdown: number
  winRate: number
  profitLossRatio: number
  tradeCount: number
  profitTrades: number
  lossTrades: number
  finalCapital: number
  annualizedReturn: number
  sharpeRatio: number
  equityCurve: { date: string; value: number }[]
  drawdownCurve: { date: string; value: number }[]
  trades: BacktestTrade[]
}

interface StrategyCompare {
  strategy_name: string
  result: BacktestResult
}

const defaultParams: BacktestParams = {
  code: 'sh600519',
  buyCondition: 'ma_break',
  sellCondition: 'stop_profit_loss',
  holdPeriod: 5,
  startDate: '2024-01-01',
  endDate: '2024-06-01',
  initialCapital: 100000,
  stopLossPct: 3,
  takeProfitPct: 5,
  maPeriod: 5,
  volumeRatioThreshold: 1.5,
}

const conditionOptions = [
  { value: 'ma_break', label: '突破均线+放量' },
  { value: 'ma_support', label: '回踩均线支撑' },
  { value: 'limit_up_break', label: '涨停突破' },
  { value: 'volume_price_rise', label: '量价齐升' },
]

const sellConditionOptions = [
  { value: 'stop_profit_loss', label: '固定止盈止损' },
  { value: 'ma_break', label: '跌破均线' },
  { value: 'trailing_stop', label: '移动止盈' },
]

const BacktestPanel: React.FC = () => {
  const [params, setParams] = useState<BacktestParams>(defaultParams)
  const [result, setResult] = useState<BacktestResult | null>(null)
  const [compareResults, setCompareResults] = useState<StrategyCompare[] | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [activeTab, setActiveTab] = useState<'result' | 'compare'>('result')
  const equityRef = useRef<HTMLCanvasElement>(null)
  const drawdownRef = useRef<HTMLCanvasElement>(null)

  const runBacktest = useCallback(async () => {
    setLoading(true)
    setError('')
    setCompareResults(null)
    setActiveTab('result')
    try {
      const res = await fetch('/api/backtest/run', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: params.code,
          buy_condition: params.buyCondition,
          sell_condition: params.sellCondition,
          hold_period: params.holdPeriod,
          start_date: params.startDate,
          end_date: params.endDate,
          initial_capital: params.initialCapital,
          stop_loss_pct: params.stopLossPct / 100,
          take_profit_pct: params.takeProfitPct / 100,
          ma_period: params.maPeriod,
          volume_ratio_threshold: params.volumeRatioThreshold,
        }),
      })
      if (!res.ok) throw new Error('回测请求失败')
      const json = await res.json()
      if (json.result) {
        setResult(json.result)
      } else {
        throw new Error('回测结果为空')
      }
    } catch (e: any) {
      setError(e.message || '回测失败')
      console.warn('回测API调用失败:', e)
    } finally {
      setLoading(false)
    }
  }, [params])

  const runCompare = useCallback(async () => {
    setLoading(true)
    setError('')
    setResult(null)
    setActiveTab('compare')
    try {
      const strategies = [
        { name: '突破均线+放量', buy_condition: 'ma_break', sell_condition: 'stop_profit_loss', hold_period: 5 },
        { name: '回踩均线支撑', buy_condition: 'ma_support', sell_condition: 'stop_profit_loss', hold_period: 3 },
        { name: '量价齐升', buy_condition: 'volume_price_rise', sell_condition: 'trailing_stop', hold_period: 5 },
      ]
      const res = await fetch('/api/backtest/compare', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: params.code,
          start_date: params.startDate,
          end_date: params.endDate,
          strategies,
        }),
      })
      if (!res.ok) throw new Error('对比请求失败')
      const json = await res.json()
      if (json.results) {
        setCompareResults(json.results)
      } else {
        throw new Error('对比结果为空')
      }
    } catch (e: any) {
      setError(e.message || '对比失败')
    } finally {
      setLoading(false)
    }
  }, [params])

  const exportReport = useCallback(() => {
    if (!result) return
    const report = {
      params,
      result: {
        ...result,
        equityCurve: result.equityCurve.slice(0, 10),
        drawdownCurve: result.drawdownCurve.slice(0, 10),
      },
      exportTime: new Date().toISOString(),
    }
    const blob = new Blob([JSON.stringify(report, null, 2)], { type: 'application/json' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `backtest_report_${params.code}_${params.startDate}_${params.endDate}.json`
    a.click()
    URL.revokeObjectURL(url)
  }, [result, params])

  const drawChart = useCallback((canvasRef: React.RefObject<HTMLCanvasElement>, data: { date: string; value: number }[], color: string, title: string) => {
    if (!data?.length || !canvasRef.current) return
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

    const values = data.map(d => d.value)
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
    const step = chartW / (data.length - 1 || 1)
    ctx.strokeStyle = color
    ctx.lineWidth = 2
    ctx.beginPath()
    data.forEach((point, i) => {
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
    ctx.fillStyle = color.replace(')', ', 0.1)').replace('rgb', 'rgba').replace('#', '')
    if (color.startsWith('#')) {
      ctx.fillStyle = color + '1A'
    }
    ctx.fill()

    // X labels
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    const xStep = Math.ceil(data.length / 6)
    for (let i = 0; i < data.length; i += xStep) {
      const x = padding.left + i * step
      ctx.fillText(data[i].date.slice(5), x, height - 8)
    }

    // Title
    ctx.fillStyle = '#E8ECF4'
    ctx.font = 'bold 12px sans-serif'
    ctx.textAlign = 'left'
    ctx.fillText(title, padding.left, padding.top - 6)
  }, [])

  useEffect(() => {
    if (result?.equityCurve?.length) {
      drawChart(equityRef, result.equityCurve, '#00D4AA', '收益曲线')
    }
  }, [result?.equityCurve, drawChart])

  useEffect(() => {
    if (result?.drawdownCurve?.length) {
      drawChart(drawdownRef, result.drawdownCurve, '#FF6B6B', '回撤曲线')
    }
  }, [result?.drawdownCurve, drawChart])

  const handleParamChange = (key: keyof BacktestParams, value: string | number) => {
    setParams(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>策略回测</h3>
        <div style={{ display: 'flex', gap: 8 }}>
          <button style={styles.runBtn} onClick={runBacktest} disabled={loading}>
            {loading ? '回测中...' : '运行回测'}
          </button>
          <button style={styles.compareBtn} onClick={runCompare} disabled={loading}>
            多策略对比
          </button>
        </div>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {/* 参数设置 */}
      <div style={styles.paramsCard}>
        <div style={styles.paramsTitle}>策略参数</div>
        <div style={styles.paramGrid}>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>股票代码</label>
            <input
              style={styles.paramInput}
              value={params.code}
              onChange={e => handleParamChange('code', e.target.value)}
              placeholder="如: sh600519"
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>买入条件</label>
            <select
              style={styles.paramInput}
              value={params.buyCondition}
              onChange={e => handleParamChange('buyCondition', e.target.value)}
            >
              {conditionOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>卖出条件</label>
            <select
              style={styles.paramInput}
              value={params.sellCondition}
              onChange={e => handleParamChange('sellCondition', e.target.value)}
            >
              {sellConditionOptions.map(o => <option key={o.value} value={o.value}>{o.label}</option>)}
            </select>
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
            <label style={styles.paramLabel}>止损比例 (%)</label>
            <input
              style={styles.paramInput}
              type="number"
              min={1}
              max={20}
              step={0.5}
              value={params.stopLossPct}
              onChange={e => handleParamChange('stopLossPct', parseFloat(e.target.value) || 3)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>止盈比例 (%)</label>
            <input
              style={styles.paramInput}
              type="number"
              min={1}
              max={50}
              step={0.5}
              value={params.takeProfitPct}
              onChange={e => handleParamChange('takeProfitPct', parseFloat(e.target.value) || 5)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>均线周期</label>
            <input
              style={styles.paramInput}
              type="number"
              min={3}
              max={60}
              value={params.maPeriod}
              onChange={e => handleParamChange('maPeriod', parseInt(e.target.value) || 5)}
            />
          </div>
          <div style={styles.paramItem}>
            <label style={styles.paramLabel}>量比阈值</label>
            <input
              style={styles.paramInput}
              type="number"
              min={1}
              max={10}
              step={0.1}
              value={params.volumeRatioThreshold}
              onChange={e => handleParamChange('volumeRatioThreshold', parseFloat(e.target.value) || 1.5)}
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

      {/* Tab切换 */}
      {(result || compareResults) && (
        <div style={styles.tabBar}>
          {result && (
            <button
              style={{ ...styles.tabBtn, ...(activeTab === 'result' ? styles.tabBtnActive : {}) }}
              onClick={() => setActiveTab('result')}
            >
              回测结果
            </button>
          )}
          {compareResults && (
            <button
              style={{ ...styles.tabBtn, ...(activeTab === 'compare' ? styles.tabBtnActive : {}) }}
              onClick={() => setActiveTab('compare')}
            >
              策略对比
            </button>
          )}
          {result && (
            <button style={styles.exportBtn} onClick={exportReport}>
              导出报告
            </button>
          )}
        </div>
      )}

      {/* 回测结果 */}
      {activeTab === 'result' && result && (
        <>
          <div style={styles.resultGrid}>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>总收益率</div>
              <div style={{ ...styles.resultValue, color: result.totalReturn >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {result.totalReturn >= 0 ? '+' : ''}{result.totalReturn.toFixed(2)}%
              </div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>年化收益率</div>
              <div style={{ ...styles.resultValue, color: result.annualizedReturn >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {result.annualizedReturn >= 0 ? '+' : ''}{result.annualizedReturn.toFixed(2)}%
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
              <div style={styles.resultLabel}>盈亏比</div>
              <div style={{ ...styles.resultValue, color: result.profitLossRatio >= 1 ? '#00D4AA' : '#FFB84D' }}>
                {result.profitLossRatio.toFixed(2)}
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
              <div style={styles.resultLabel}>夏普比率</div>
              <div style={{ ...styles.resultValue, color: result.sharpeRatio >= 1 ? '#00D4AA' : '#E8ECF4' }}>
                {result.sharpeRatio.toFixed(2)}
              </div>
            </div>
            <div style={styles.resultCard}>
              <div style={styles.resultLabel}>最终资金</div>
              <div style={{ ...styles.resultValue, color: '#E8ECF4' }}>
                ¥{result.finalCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </div>
            </div>
          </div>

          {/* 图表 */}
          <div style={styles.chartCard}>
            <canvas ref={equityRef} style={styles.canvas} />
          </div>
          <div style={styles.chartCard}>
            <canvas ref={drawdownRef} style={styles.canvas} />
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
                    <th style={styles.th}>原因</th>
                  </tr>
                </thead>
                <tbody>
                  {result.trades.length === 0 ? (
                    <tr>
                      <td colSpan={8} style={{ ...styles.td, textAlign: 'center', color: '#5A6B87', padding: '24px' }}>
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
                              {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)} ({t.pnlPct?.toFixed(2)}%)
                            </span>
                          ) : (
                            <span style={{ color: '#5A6B87' }}>--</span>
                          )}
                        </td>
                        <td style={{ ...styles.td, fontSize: '12px', color: '#7A8BA7' }}>{t.reason || '--'}</td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>
        </>
      )}

      {/* 策略对比 */}
      {activeTab === 'compare' && compareResults && (
        <div style={styles.compareSection}>
          <div style={styles.tradesTitle}>多策略对比</div>
          <div style={styles.tableContainer}>
            <table style={styles.table}>
              <thead>
                <tr>
                  <th style={styles.th}>策略名称</th>
                  <th style={styles.th}>总收益率</th>
                  <th style={styles.th}>最大回撤</th>
                  <th style={styles.th}>胜率</th>
                  <th style={styles.th}>盈亏比</th>
                  <th style={styles.th}>交易次数</th>
                  <th style={styles.th}>最终资金</th>
                  <th style={styles.th}>夏普比率</th>
                </tr>
              </thead>
              <tbody>
                {compareResults.map((r, idx) => (
                  <tr key={idx} style={styles.tr}>
                    <td style={{ ...styles.td, fontWeight: 600 }}>{r.strategy_name}</td>
                    <td style={{ ...styles.td, color: r.result.totalReturn >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                      {r.result.totalReturn >= 0 ? '+' : ''}{r.result.totalReturn.toFixed(2)}%
                    </td>
                    <td style={{ ...styles.td, color: '#FF6B6B' }}>-{r.result.maxDrawdown.toFixed(2)}%</td>
                    <td style={{ ...styles.td, color: r.result.winRate >= 50 ? '#00D4AA' : '#FFB84D' }}>
                      {r.result.winRate.toFixed(2)}%
                    </td>
                    <td style={styles.td}>{r.result.profitLossRatio.toFixed(2)}</td>
                    <td style={styles.td}>{r.result.tradeCount}</td>
                    <td style={styles.td}>¥{r.result.finalCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</td>
                    <td style={styles.td}>{r.result.sharpeRatio.toFixed(2)}</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
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
  compareBtn: {
    padding: '6px 16px',
    border: '1px solid #00D4AA',
    borderRadius: '6px',
    background: 'transparent',
    color: '#00D4AA',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  exportBtn: {
    padding: '4px 12px',
    border: '1px solid #5A6B87',
    borderRadius: '4px',
    background: 'transparent',
    color: '#5A6B87',
    fontSize: '12px',
    cursor: 'pointer',
    marginLeft: 'auto',
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
    gridTemplateColumns: 'repeat(auto-fill, minmax(180px, 1fr))',
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
  tabBar: {
    display: 'flex',
    gap: '8px',
    alignItems: 'center',
    borderBottom: '1px solid #243050',
    paddingBottom: '8px',
  },
  tabBtn: {
    padding: '6px 14px',
    border: 'none',
    borderRadius: '4px',
    background: 'transparent',
    color: '#7A8BA7',
    fontSize: '13px',
    cursor: 'pointer',
  },
  tabBtnActive: {
    background: '#1A2540',
    color: '#00D4AA',
    fontWeight: 600,
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
    height: '240px',
    display: 'block',
  },
  tradesSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  compareSection: {
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
