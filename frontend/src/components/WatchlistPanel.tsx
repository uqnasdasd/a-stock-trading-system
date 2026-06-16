import React, { useState, useEffect, useCallback } from 'react'

interface WatchlistStock {
  code: string
  name: string
  price: number
  change_pct: number
  open: number
  high: number
  low: number
  volume: number
  pre_close: number
}

interface Props {
  onStockClick?: (code: string, name: string) => void
}

const WatchlistPanel: React.FC<Props> = ({ onStockClick }) => {
  const [stocks, setStocks] = useState<WatchlistStock[]>([])
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  const fetchWatchlist = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/watchlist')
      const json = await res.json()
      if (json.stocks) {
        setStocks(json.stocks)
      }
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    } catch (e) {
      console.error('自选股获取失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchWatchlist()
    const timer = setInterval(fetchWatchlist, 5000)
    return () => clearInterval(timer)
  }, [fetchWatchlist])

  const removeStock = async (code: string) => {
    try {
      await fetch(`/api/watchlist/${code}`, { method: 'DELETE' })
      setStocks(prev => prev.filter(s => s.code !== code))
    } catch (e) {
      console.error('删除自选股失败:', e)
    }
  }

  const isAlert = (changePct: number) => Math.abs(changePct) > 3

  const formatVolume = (vol: number) => {
    if (vol >= 100000000) return (vol / 100000000).toFixed(2) + '亿'
    if (vol >= 10000) return (vol / 10000).toFixed(0) + '万'
    return vol.toString()
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>自选股</h3>
        <div style={styles.headerRight}>
          {loading && <span style={styles.loadingDot}>刷新中</span>}
          {lastUpdate && <span style={styles.lastUpdate}>{lastUpdate}</span>}
        </div>
      </div>

      {stocks.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyText}>暂无自选股</div>
          <div style={styles.emptySub}>通过股票搜索添加自选股</div>
        </div>
      ) : (
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>股票</th>
                <th style={styles.th}>现价</th>
                <th style={styles.th}>涨跌幅</th>
                <th style={styles.th}>最高</th>
                <th style={styles.th}>最低</th>
                <th style={styles.th}>成交量</th>
                <th style={styles.th}>操作</th>
              </tr>
            </thead>
            <tbody>
              {stocks.map((stock) => {
                const alert = isAlert(stock.change_pct)
                const color = stock.change_pct >= 0 ? '#00D4AA' : '#FF6B6B'
                return (
                  <tr
                    key={stock.code}
                    style={{
                      ...styles.tr,
                      background: alert
                        ? stock.change_pct > 0
                          ? 'rgba(255,107,107,0.1)'
                          : 'rgba(0,212,170,0.1)'
                        : 'transparent',
                      cursor: onStockClick ? 'pointer' : 'default',
                    }}
                    onClick={() => onStockClick?.(stock.code, stock.name)}
                  >
                    <td style={styles.td}>
                      <div style={styles.stockName}>{stock.name}</div>
                      <div style={styles.stockCode}>{stock.code}</div>
                    </td>
                    <td style={{ ...styles.td, color, fontWeight: 600, fontFamily: 'monospace' }}>
                      {stock.price?.toFixed(2)}
                    </td>
                    <td style={{ ...styles.td, color, fontWeight: 600, fontFamily: 'monospace' }}>
                      {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
                      {alert && (
                        <span style={styles.alertBadge}>
                          {stock.change_pct > 3 ? '异动' : '异动'}
                        </span>
                      )}
                    </td>
                    <td style={{ ...styles.td, fontFamily: 'monospace' }}>
                      {stock.high?.toFixed(2)}
                    </td>
                    <td style={{ ...styles.td, fontFamily: 'monospace' }}>
                      {stock.low?.toFixed(2)}
                    </td>
                    <td style={{ ...styles.td, fontFamily: 'monospace', color: '#7A8BA7' }}>
                      {formatVolume(stock.volume)}
                    </td>
                    <td style={styles.td}>
                      <button
                        style={styles.deleteBtn}
                        onClick={(e) => {
                          e.stopPropagation()
                          removeStock(stock.code)
                        }}
                      >
                        删除
                      </button>
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
        </div>
      )}

      <div style={styles.alertNote}>
        <span style={styles.alertDot} />
        涨跌幅超过3%时自动高亮提醒
      </div>
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
  stockName: {
    fontWeight: 600,
    fontSize: '13px',
  },
  stockCode: {
    fontSize: '11px',
    color: '#7A8BA7',
    fontFamily: 'monospace',
  },
  alertBadge: {
    display: 'inline-block',
    marginLeft: '6px',
    padding: '1px 5px',
    borderRadius: '3px',
    fontSize: '10px',
    fontWeight: 600,
    background: 'rgba(255,184,77,0.25)',
    color: '#FFB84D',
    border: '1px solid rgba(255,184,77,0.4)',
  },
  deleteBtn: {
    padding: '3px 8px',
    background: 'rgba(255,107,107,0.15)',
    color: '#FF6B6B',
    border: '1px solid rgba(255,107,107,0.3)',
    borderRadius: '4px',
    fontSize: '11px',
    cursor: 'pointer',
    fontWeight: 600,
  },
  alertNote: {
    display: 'flex',
    alignItems: 'center',
    gap: '6px',
    fontSize: '11px',
    color: '#5A6B87',
    paddingTop: '4px',
  },
  alertDot: {
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: '#FFB84D',
    flexShrink: 0,
  },
}

export { WatchlistPanel }
export default WatchlistPanel
