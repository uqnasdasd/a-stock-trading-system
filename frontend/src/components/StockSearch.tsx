import React, { useState } from 'react'
import KlineChart from './KlineChart'
import MinuteChart from './MinuteChart'

interface StockInfo {
  code: string
  name: string
  price: number
  change_pct: number
  open: number
  high: number
  low: number
  pre_close: number
  volume: number
}

const StockSearch: React.FC = () => {
  const [query, setQuery] = useState('')
  const [stock, setStock] = useState<StockInfo | null>(null)
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')
  const [showChart, setShowChart] = useState(false)
  const [showMinute, setShowMinute] = useState(false)
  const [watchlistAdded, setWatchlistAdded] = useState(false)

  const search = async () => {
    if (!query.trim()) return
    setLoading(true)
    setError('')
    setShowChart(false)
    setShowMinute(false)
    try {
      const res = await fetch(`/api/stock/search?code=${encodeURIComponent(query)}`)
      const data = await res.json()
      if (data.found) {
        setStock(data)
      } else {
        setError(data.message || '未找到')
        setStock(null)
      }
    } catch (e) {
      setError('请求失败')
    } finally {
      setLoading(false)
    }
  }

  const addWatchlist = async () => {
    if (!stock) return
    try {
      const res = await fetch('/api/watchlist', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ code: stock.code, name: stock.name }),
      })
      const json = await res.json()
      if (json.success !== false) {
        setWatchlistAdded(true)
        setTimeout(() => setWatchlistAdded(false), 3000)
      }
    } catch (e) {
      console.error('添加自选股失败:', e)
    }
  }

  const addPosition = async () => {
    if (!stock) return
    const volume = parseInt(prompt(`买入 ${stock.name}(${stock.code}) 多少股？`, '100') || '0')
    if (!volume) return

    try {
      const res = await fetch('/api/positions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: stock.code,
          name: stock.name,
          buy_price: stock.price,
          current_price: stock.price,
          volume,
          sector: '',
          buy_time: new Date().toISOString(),
          stop_loss_price: +(stock.price * 0.97).toFixed(2),
          take_profit_price: +(stock.price * 1.05).toFixed(2),
        }),
      })
      const data = await res.json()
      alert(data.message || '添加成功')
    } catch (e) {
      alert('添加失败')
    }
  }

  return (
    <div style={styles.container}>
      <div style={styles.searchRow}>
        <input
          style={styles.input}
          placeholder="输入股票代码 (如: 600519 或 sh600519)"
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && search()}
        />
        <button style={styles.button} onClick={search} disabled={loading}>
          {loading ? '搜索中...' : '搜索'}
        </button>
      </div>

      {error && <div style={styles.error}>{error}</div>}

      {stock && (
        <div style={styles.stockCard}>
          <div style={styles.stockHeader}>
            <span style={styles.stockName}>{stock.name}</span>
            <span style={styles.stockCode}>{stock.code}</span>
          </div>
          <div style={styles.stockPriceRow}>
            <span style={{ ...styles.stockPrice, color: stock.change_pct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
              ¥{stock.price?.toFixed(2)}
            </span>
            <span style={{ ...styles.stockChange, color: stock.change_pct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
              {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct?.toFixed(2)}%
            </span>
          </div>
          <div style={styles.stockDetail}>
            <span>开: {stock.open?.toFixed(2)}</span>
            <span>高: {stock.high?.toFixed(2)}</span>
            <span>低: {stock.low?.toFixed(2)}</span>
            <span>量: {(stock.volume / 10000)?.toFixed(0)}万</span>
          </div>
          <div style={styles.btnRow}>
            <button style={styles.addBtn} onClick={addPosition}>
              + 加入持仓
            </button>
            <button
              style={{
                ...styles.watchlistBtn,
                background: watchlistAdded ? 'rgba(255,184,77,0.2)' : '#243050',
                color: watchlistAdded ? '#FFB84D' : '#E8ECF4',
                border: watchlistAdded ? '1px solid rgba(255,184,77,0.4)' : '1px solid #243050',
              }}
              onClick={addWatchlist}
            >
              {watchlistAdded ? '已加自选' : '+ 自选股'}
            </button>
            <button style={styles.chartBtn} onClick={() => setShowChart(!showChart)}>
              {showChart ? '隐藏K线' : '查看K线'}
            </button>
            <button style={styles.minuteBtn} onClick={() => setShowMinute(!showMinute)}>
              {showMinute ? '隐藏分时' : '查看分时'}
            </button>
          </div>
          {showChart && stock && <KlineChart code={stock.code} name={stock.name} />}
          {showMinute && stock && <MinuteChart code={stock.code} name={stock.name} />}
        </div>
      )}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    marginBottom: '16px',
  },
  searchRow: {
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
  button: {
    padding: '8px 16px',
    background: '#00D4AA',
    color: '#0B1120',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  error: {
    color: '#FF6B6B',
    fontSize: '12px',
    marginTop: '6px',
  },
  stockCard: {
    marginTop: '12px',
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  stockHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '8px',
  },
  stockName: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#E8ECF4',
  },
  stockCode: {
    fontSize: '12px',
    color: '#7A8BA7',
    fontFamily: 'monospace',
  },
  stockPriceRow: {
    display: 'flex',
    alignItems: 'baseline',
    gap: '12px',
    marginBottom: '8px',
  },
  stockPrice: {
    fontSize: '24px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  stockChange: {
    fontSize: '14px',
    fontWeight: 600,
  },
  stockDetail: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '10px',
  },
  btnRow: {
    display: 'flex',
    gap: '8px',
  },
  addBtn: {
    flex: 1,
    padding: '8px',
    background: '#00D4AA',
    color: '#0B1120',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  chartBtn: {
    flex: 1,
    padding: '8px',
    background: '#243050',
    color: '#E8ECF4',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  watchlistBtn: {
    flex: 1,
    padding: '8px',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  minuteBtn: {
    flex: 1,
    padding: '8px',
    background: '#243050',
    color: '#E8ECF4',
    border: 'none',
    borderRadius: '6px',
    fontSize: '14px',
    fontWeight: 600,
    cursor: 'pointer',
  },
}

export default StockSearch
