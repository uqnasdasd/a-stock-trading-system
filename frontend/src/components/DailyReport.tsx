import React, { useState, useEffect, useCallback } from 'react'

interface TradeRecord {
  time: string
  code: string
  name: string
  action: string
  price: number
  volume: number
  reason?: string
  pnl?: number
}

interface PositionChange {
  code: string
  name: string
  action: string
  price?: number
  volume?: number
  time?: string
  buy_price?: number
  current_price?: number
  profit_pct?: number
  market_value?: number
  pnl?: number
  is_new_position?: boolean
}

interface SignalStats {
  stop_loss: number
  take_profit: number
  risk_alert: number
  position_sell: number
  total: number
}

interface SectorItem {
  name: string
  avg_change_pct: number
  stock_count: number
  up_count: number
  down_count: number
}

interface RiskRecord {
  time: string
  type: string
  level: string
  message: string
}

interface ReportSummary {
  total_pnl: number
  return_pct: number
  total_capital: number
  trade_count: number
  buy_count: number
  sell_count: number
  realized_pnl: number
  unrealized_pnl: number
}

interface DailyReportData {
  date: string
  generated_at: string
  summary: ReportSummary
  trades: TradeRecord[]
  position_changes: PositionChange[]
  signal_stats: SignalStats
  sector_performance: SectorItem[]
  risk_records: RiskRecord[]
  suggestions: string[]
}

const DailyReport: React.FC = () => {
  const [report, setReport] = useState<DailyReportData | null>(null)
  const [loading, setLoading] = useState(false)

  const fetchReport = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/report/daily')
      const json = await res.json()
      setReport(json)
    } catch (e) {
      console.error('获取复盘报告失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchReport()
  }, [fetchReport])

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      hour12: false,
    })
  }

  const getActionStyle = (action: string): React.CSSProperties => {
    if (action === '买入' || action === 'buy') {
      return {
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 600,
        background: 'rgba(0,212,170,0.15)',
        color: '#00D4AA',
        border: '1px solid rgba(0,212,170,0.3)',
      }
    }
    if (action === '卖出' || action === 'sell') {
      return {
        padding: '2px 8px',
        borderRadius: '4px',
        fontSize: '12px',
        fontWeight: 600,
        background: 'rgba(255,107,107,0.15)',
        color: '#FF6B6B',
        border: '1px solid rgba(255,107,107,0.3)',
      }
    }
    return {
      padding: '2px 8px',
      borderRadius: '4px',
      fontSize: '12px',
      fontWeight: 600,
      background: 'rgba(255,184,77,0.15)',
      color: '#FFB84D',
      border: '1px solid rgba(255,184,77,0.3)',
    }
  }

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'emergency':
        return { bg: '#3D1515', border: '#FF4444', text: '#FF6B6B' }
      case 'important':
        return { bg: '#3D1F0D', border: '#FF8800', text: '#FFAA44' }
      case 'normal':
        return { bg: '#3D320D', border: '#FFCC00', text: '#FFDD55' }
      default:
        return { bg: '#0F2744', border: '#00A8FF', text: '#44BBFF' }
    }
  }

  const exportCSV = () => {
    if (!report) return
    const headers = ['日期', '当日盈亏', '收益率', '交易次数', '买入次数', '卖出次数', '已实现盈亏', '浮动盈亏']
    const s = report.summary
    const summaryRow = [
      report.date,
      s?.total_pnl?.toFixed(2) ?? '0',
      `${s?.return_pct?.toFixed(2) ?? '0'}%`,
      String(s?.trade_count ?? 0),
      String(s?.buy_count ?? 0),
      String(s?.sell_count ?? 0),
      s?.realized_pnl?.toFixed(2) ?? '0',
      s?.unrealized_pnl?.toFixed(2) ?? '0',
    ]

    const tradeHeaders = ['时间', '代码', '名称', '操作', '价格', '数量', '盈亏']
    const tradeRows = report.trades.map(t => [
      t.time,
      t.code,
      t.name,
      t.action === 'buy' ? '买入' : t.action === 'sell' ? '卖出' : t.action,
      t.price?.toFixed(2) ?? '',
      String(t.volume),
      t.pnl !== undefined ? t.pnl.toFixed(2) : '--',
    ])

    const posHeaders = ['股票', '状态', '成本/现价', '数量', '盈亏', '市值']
    const posRows = report.position_changes.map(pc => [
      `${pc.name}(${pc.code})`,
      pc.action,
      pc.buy_price !== undefined ? `${pc.buy_price.toFixed(2)} / ${pc.current_price?.toFixed(2) ?? '--'}` : pc.price?.toFixed(2) ?? '--',
      String(pc.volume ?? '--'),
      pc.profit_pct !== undefined ? `${pc.profit_pct >= 0 ? '+' : ''}${pc.profit_pct.toFixed(2)}%` : pc.pnl !== undefined ? pc.pnl.toFixed(2) : '--',
      pc.market_value !== undefined ? pc.market_value.toFixed(2) : '--',
    ])

    const csvLines: string[] = []
    csvLines.push('=== 每日复盘报告 ===')
    csvLines.push('')
    csvLines.push(headers.join(','))
    csvLines.push(summaryRow.map(c => `"${String(c).replace(/"/g, '""')}"`).join(','))
    csvLines.push('')
    csvLines.push('=== 交易记录 ===')
    csvLines.push(tradeHeaders.join(','))
    tradeRows.forEach(row => csvLines.push(row.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')))
    csvLines.push('')
    csvLines.push('=== 持仓变化 ===')
    csvLines.push(posHeaders.join(','))
    posRows.forEach(row => csvLines.push(row.map(c => `"${String(c).replace(/"/g, '""')}"`).join(',')))

    const csv = '\uFEFF' + csvLines.join('\n')
    const blob = new Blob([csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `每日复盘_${report.date}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const summary = report?.summary
  const isProfit = (summary?.total_pnl || 0) >= 0
  const isProfitPct = (summary?.return_pct || 0) >= 0

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>每日复盘报告</h3>
        <div style={styles.headerRight}>
          {report?.generated_at && (
            <span style={styles.generatedAt}>生成时间: {formatTime(report.generated_at)}</span>
          )}
          <button style={styles.exportBtn} onClick={exportCSV} disabled={!report}>
            导出CSV
          </button>
          <button style={styles.refreshBtn} onClick={fetchReport} disabled={loading}>
            {loading ? '生成中...' : '重新生成'}
          </button>
        </div>
      </div>

      {!report ? (
        <div style={styles.empty}>
          <div style={styles.emptyText}>暂无复盘报告</div>
          <div style={styles.emptySub}>点击右上角重新生成</div>
        </div>
      ) : (
        <div style={styles.content}>
          {/* 盈亏概览 */}
          <div style={styles.overview}>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>当日盈亏</div>
              <div style={{ ...styles.overviewValue, color: isProfit ? '#00D4AA' : '#FF6B6B' }}>
                {isProfit ? '+' : ''}{summary?.total_pnl.toFixed(2)}
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>收益率</div>
              <div style={{ ...styles.overviewValue, color: isProfitPct ? '#00D4AA' : '#FF6B6B' }}>
                {isProfitPct ? '+' : ''}{summary?.return_pct.toFixed(2)}%
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>交易次数</div>
              <div style={styles.overviewValue}>{summary?.trade_count || 0}</div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>买入 / 卖出</div>
              <div style={styles.overviewValue}>
                <span style={{ color: '#00D4AA' }}>{summary?.buy_count || 0}</span>
                <span style={{ color: '#5A6B87', margin: '0 4px' }}>/</span>
                <span style={{ color: '#FF6B6B' }}>{summary?.sell_count || 0}</span>
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>已实现盈亏</div>
              <div style={{ ...styles.overviewValue, color: (summary?.realized_pnl || 0) >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {(summary?.realized_pnl || 0) >= 0 ? '+' : ''}{summary?.realized_pnl.toFixed(2)}
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>浮动盈亏</div>
              <div style={{ ...styles.overviewValue, color: (summary?.unrealized_pnl || 0) >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {(summary?.unrealized_pnl || 0) >= 0 ? '+' : ''}{summary?.unrealized_pnl.toFixed(2)}
              </div>
            </div>
          </div>

          {/* 交易记录 */}
          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>交易记录汇总</h4>
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>时间</th>
                    <th style={styles.th}>代码</th>
                    <th style={styles.th}>名称</th>
                    <th style={styles.th}>操作</th>
                    <th style={styles.th}>价格</th>
                    <th style={styles.th}>数量</th>
                    <th style={styles.th}>盈亏</th>
                  </tr>
                </thead>
                <tbody>
                  {report.trades.length === 0 ? (
                    <tr>
                      <td colSpan={7} style={{ ...styles.td, textAlign: 'center', color: '#5A6B87', padding: '24px' }}>
                        今日暂无交易记录
                      </td>
                    </tr>
                  ) : (
                    report.trades.map((t, idx) => (
                      <tr key={idx} style={styles.tr}>
                        <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: '12px', color: '#7A8BA7' }}>
                          {formatTime(t.time)}
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>{t.code}</td>
                        <td style={{ ...styles.td, fontWeight: 600 }}>{t.name}</td>
                        <td style={styles.td}>
                          <span style={getActionStyle(t.action)}>
                            {t.action === 'buy' ? '买入' : t.action === 'sell' ? '卖出' : t.action}
                          </span>
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace', fontWeight: 600 }}>
                          {t.price.toFixed(2)}
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>{t.volume}</td>
                        <td style={styles.td}>
                          {t.pnl !== undefined ? (
                            <span style={{ color: t.pnl >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                              {t.pnl >= 0 ? '+' : ''}{t.pnl.toFixed(2)}
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

          {/* 持仓变化 */}
          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>持仓变化</h4>
            <div style={styles.tableContainer}>
              <table style={styles.table}>
                <thead>
                  <tr>
                    <th style={styles.th}>股票</th>
                    <th style={styles.th}>状态</th>
                    <th style={styles.th}>成本/现价</th>
                    <th style={styles.th}>数量</th>
                    <th style={styles.th}>盈亏</th>
                    <th style={styles.th}>市值</th>
                  </tr>
                </thead>
                <tbody>
                  {report.position_changes.length === 0 ? (
                    <tr>
                      <td colSpan={6} style={{ ...styles.td, textAlign: 'center', color: '#5A6B87', padding: '24px' }}>
                        暂无持仓变化
                      </td>
                    </tr>
                  ) : (
                    report.position_changes.map((pc, idx) => (
                      <tr key={idx} style={styles.tr}>
                        <td style={styles.td}>
                          <div style={{ fontWeight: 600 }}>{pc.name}</div>
                          <div style={{ fontSize: '12px', color: '#7A8BA7' }}>{pc.code}</div>
                        </td>
                        <td style={styles.td}>
                          <span style={getActionStyle(pc.action)}>{pc.action}</span>
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>
                          {pc.buy_price !== undefined ? (
                            <span>
                              {pc.buy_price.toFixed(2)} / {pc.current_price?.toFixed(2)}
                            </span>
                          ) : pc.price !== undefined ? (
                            <span>{pc.price.toFixed(2)}</span>
                          ) : (
                            <span style={{ color: '#5A6B87' }}>--</span>
                          )}
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>{pc.volume || '--'}</td>
                        <td style={styles.td}>
                          {pc.profit_pct !== undefined ? (
                            <span style={{ color: pc.profit_pct >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                              {pc.profit_pct >= 0 ? '+' : ''}{pc.profit_pct.toFixed(2)}%
                            </span>
                          ) : pc.pnl !== undefined ? (
                            <span style={{ color: pc.pnl >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                              {pc.pnl >= 0 ? '+' : ''}{pc.pnl.toFixed(2)}
                            </span>
                          ) : (
                            <span style={{ color: '#5A6B87' }}>--</span>
                          )}
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>
                          {pc.market_value !== undefined ? pc.market_value.toFixed(2) : '--'}
                        </td>
                      </tr>
                    ))
                  )}
                </tbody>
              </table>
            </div>
          </div>

          <div style={styles.twoColumn}>
            {/* 信号统计 */}
            <div style={styles.section}>
              <h4 style={styles.sectionTitle}>信号统计</h4>
              <div style={styles.statsGrid}>
                <div style={styles.statItem}>
                  <div style={styles.statLabel}>止损</div>
                  <div style={{ ...styles.statValue, color: '#FF6B6B' }}>{report.signal_stats.stop_loss}</div>
                </div>
                <div style={styles.statItem}>
                  <div style={styles.statLabel}>止盈</div>
                  <div style={{ ...styles.statValue, color: '#00D4AA' }}>{report.signal_stats.take_profit}</div>
                </div>
                <div style={styles.statItem}>
                  <div style={styles.statLabel}>风控</div>
                  <div style={{ ...styles.statValue, color: '#FFB84D' }}>{report.signal_stats.risk_alert}</div>
                </div>
                <div style={styles.statItem}>
                  <div style={styles.statLabel}>清仓</div>
                  <div style={{ ...styles.statValue, color: '#FFAA44' }}>{report.signal_stats.position_sell}</div>
                </div>
              </div>
              <div style={styles.statTotal}>
                信号总计: <span style={{ fontWeight: 700, color: '#E8ECF4' }}>{report.signal_stats.total}</span>
              </div>
            </div>

            {/* 板块表现 TOP3 */}
            <div style={styles.section}>
              <h4 style={styles.sectionTitle}>板块表现 TOP3</h4>
              {report.sector_performance.length === 0 ? (
                <div style={{ ...styles.empty, padding: '24px' }}>
                  <div style={styles.emptySub}>暂无板块数据</div>
                </div>
              ) : (
                <div style={styles.sectorList}>
                  {report.sector_performance.map((s, idx) => (
                    <div key={idx} style={styles.sectorItem}>
                      <div style={styles.sectorRank}>{idx + 1}</div>
                      <div style={styles.sectorInfo}>
                        <div style={styles.sectorName}>{s.name}</div>
                        <div style={styles.sectorDetail}>
                          {s.stock_count}只 | 涨{s.up_count} 跌{s.down_count}
                        </div>
                      </div>
                      <div style={{ ...styles.sectorChange, color: s.avg_change_pct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                        {s.avg_change_pct >= 0 ? '+' : ''}{s.avg_change_pct.toFixed(2)}%
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          </div>

          {/* 风控触发记录 */}
          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>风控触发记录</h4>
            {report.risk_records.length === 0 ? (
              <div style={{ ...styles.empty, padding: '16px' }}>
                <div style={styles.emptySub}>今日未触发风控规则</div>
              </div>
            ) : (
              <div style={styles.riskList}>
                {report.risk_records.map((r, idx) => {
                  const colors = getLevelColor(r.level)
                  return (
                    <div
                      key={idx}
                      style={{
                        ...styles.riskCard,
                        background: colors.bg,
                        borderLeft: `3px solid ${colors.border}`,
                      }}
                    >
                      <div style={styles.riskHeader}>
                        <span style={{ ...styles.riskType, color: colors.text }}>{r.type}</span>
                        <span style={styles.riskTime}>{formatTime(r.time)}</span>
                      </div>
                      <div style={styles.riskMessage}>{r.message}</div>
                    </div>
                  )
                })}
              </div>
            )}
          </div>

          {/* 明日操作建议 */}
          <div style={styles.section}>
            <h4 style={styles.sectionTitle}>明日操作建议</h4>
            <div style={styles.suggestionList}>
              {report.suggestions.map((s, idx) => (
                <div key={idx} style={styles.suggestionItem}>
                  <span style={styles.suggestionDot} />
                  <span style={styles.suggestionText}>{s}</span>
                </div>
              ))}
            </div>
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
  headerRight: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  generatedAt: {
    fontSize: '12px',
    color: '#5A6B87',
  },
  exportBtn: {
    padding: '4px 12px',
    border: 'none',
    borderRadius: '4px',
    background: '#1A2540',
    color: '#00D4AA',
    fontSize: '12px',
    cursor: 'pointer',
    borderWidth: '1px',
    borderStyle: 'solid',
    borderColor: 'rgba(0,212,170,0.3)',
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
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#7A8BA7',
    padding: '40px',
  },
  emptyText: {
    fontSize: '15px',
    marginBottom: '4px',
  },
  emptySub: {
    fontSize: '12px',
    opacity: 0.6,
  },
  content: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  overview: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(140px, 1fr))',
    gap: '12px',
  },
  overviewCard: {
    padding: '14px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
    textAlign: 'center',
  },
  overviewLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '6px',
  },
  overviewValue: {
    fontSize: '20px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  section: {
    background: '#131B2E',
    borderRadius: '8px',
    border: '1px solid #243050',
    padding: '14px',
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#00D4AA',
    margin: '0 0 12px 0',
    paddingBottom: '8px',
    borderBottom: '1px solid #243050',
  },
  tableContainer: {
    overflow: 'auto',
    borderRadius: '6px',
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
  twoColumn: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '16px',
  },
  statsGrid: {
    display: 'grid',
    gridTemplateColumns: '1fr 1fr',
    gap: '10px',
  },
  statItem: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '6px',
    border: '1px solid #243050',
    textAlign: 'center',
  },
  statLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  statValue: {
    fontSize: '22px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  statTotal: {
    marginTop: '10px',
    fontSize: '13px',
    color: '#7A8BA7',
    textAlign: 'center',
  },
  sectorList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  sectorItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '10px',
    padding: '10px',
    background: '#1A2540',
    borderRadius: '6px',
    border: '1px solid #243050',
  },
  sectorRank: {
    width: '24px',
    height: '24px',
    borderRadius: '50%',
    background: '#243050',
    color: '#00D4AA',
    fontSize: '12px',
    fontWeight: 700,
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    flexShrink: 0,
  },
  sectorInfo: {
    flex: 1,
    minWidth: 0,
  },
  sectorName: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#E8ECF4',
  },
  sectorDetail: {
    fontSize: '12px',
    color: '#5A6B87',
    marginTop: '2px',
  },
  sectorChange: {
    fontSize: '16px',
    fontWeight: 700,
    fontFamily: 'monospace',
    flexShrink: 0,
  },
  riskList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  riskCard: {
    padding: '10px 12px',
    borderRadius: '6px',
  },
  riskHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
  },
  riskType: {
    fontSize: '12px',
    fontWeight: 600,
  },
  riskTime: {
    fontSize: '11px',
    color: '#5A6B87',
  },
  riskMessage: {
    fontSize: '13px',
    color: '#B8C4D4',
  },
  suggestionList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  suggestionItem: {
    display: 'flex',
    alignItems: 'flex-start',
    gap: '8px',
    padding: '10px 12px',
    background: '#1A2540',
    borderRadius: '6px',
    border: '1px solid #243050',
  },
  suggestionDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#00D4AA',
    marginTop: '6px',
    flexShrink: 0,
  },
  suggestionText: {
    fontSize: '13px',
    color: '#B8C4D4',
    lineHeight: 1.5,
  },
}

export default DailyReport
