import React, { useState, useEffect, useCallback } from 'react'

const dotStyle = (color: string): React.CSSProperties => ({
  width: '8px',
  height: '8px',
  borderRadius: '50%',
  background: color,
  flexShrink: 0,
  display: 'inline-block',
})

interface LimitStock {
  code: string
  name: string
  price: number
  change_pct: number
  seal_volume: number      // 封单量（手）
  continuous_boards: number // 连板数
  is_broken: boolean       // 是否炸板
  limit_type: 'up' | 'down'
}

interface Props {
  onStockClick?: (code: string, name: string) => void
}

const LimitMonitor: React.FC<Props> = ({ onStockClick }) => {
  const [limitUpList, setLimitUpList] = useState<LimitStock[]>([])
  const [limitDownList, setLimitDownList] = useState<LimitStock[]>([])
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/limit/stocks')
      const json = await res.json()
      if (json.limit_up) setLimitUpList(json.limit_up)
      if (json.limit_down) setLimitDownList(json.limit_down)
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    } catch (e) {
      console.error('涨跌停数据获取失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const timer = setInterval(fetchData, 5000)
    return () => clearInterval(timer)
  }, [fetchData])

  const formatVolume = (vol: number) => {
    if (vol >= 10000) return (vol / 10000).toFixed(1) + '万'
    return vol.toString()
  }

  const renderTable = (title: string, list: LimitStock[], type: 'up' | 'down') => {
    const mainColor = type === 'up' ? '#FF6B6B' : '#00D4AA'
    return (
      <div style={styles.tableSection}>
        <div style={styles.tableHeader}>
          <span style={{ ...styles.tableTitle, color: mainColor }}>
            {title}
          </span>
          <span style={styles.tableCount}>{list.length} 只</span>
        </div>
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>代码</th>
                <th style={styles.th}>名称</th>
                <th style={styles.th}>涨幅</th>
                <th style={styles.th}>封单量</th>
                <th style={styles.th}>连板</th>
              </tr>
            </thead>
            <tbody>
              {list.length === 0 ? (
                <tr>
                  <td colSpan={5} style={{ ...styles.td, textAlign: 'center', color: '#5A6B87', padding: '24px' }}>
                    暂无数据
                  </td>
                </tr>
              ) : (
                list.map((stock) => (
                  <tr
                    key={stock.code}
                    style={{
                      ...styles.tr,
                      background: stock.is_broken ? 'rgba(255,184,77,0.12)' : 'transparent',
                      cursor: onStockClick ? 'pointer' : 'default',
                    }}
                    onClick={() => onStockClick?.(stock.code, stock.name)}
                  >
                    <td style={styles.td}>
                      <span style={styles.code}>{stock.code}</span>
                    </td>
                    <td style={styles.td}>
                      <span style={styles.name}>{stock.name}</span>
                      {stock.is_broken && (
                        <span style={styles.brokenBadge}>炸板</span>
                      )}
                    </td>
                    <td style={{ ...styles.td, color: mainColor, fontWeight: 600, fontFamily: 'monospace' }}>
                      {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
                    </td>
                    <td style={{ ...styles.td, fontFamily: 'monospace' }}>
                      {formatVolume(stock.seal_volume)}手
                    </td>
                    <td style={styles.td}>
                      {stock.continuous_boards > 0 ? (
                        <span style={styles.boardBadge}>{stock.continuous_boards}板</span>
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
    )
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>涨跌停监控</h3>
        <div style={styles.headerRight}>
          {loading && <span style={styles.loadingDot}>刷新中</span>}
          {lastUpdate && <span style={styles.lastUpdate}>更新: {lastUpdate}</span>}
        </div>
      </div>

      <div style={styles.legend}>
        <span style={styles.legendItem}>
          <span style={dotStyle('#FF6B6B')} /> 涨停
        </span>
        <span style={styles.legendItem}>
          <span style={dotStyle('#00D4AA')} /> 跌停
        </span>
        <span style={styles.legendItem}>
          <span style={{ ...dotStyle('#FFB84D'), border: '1px solid #FFB84D', background: 'transparent' }} /> 炸板预警
        </span>
      </div>

      {renderTable('涨停股', limitUpList, 'up')}
      {renderTable('跌停股', limitDownList, 'down')}
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
  legend: {
    display: 'flex',
    gap: '16px',
    fontSize: '12px',
    color: '#7A8BA7',
  },
  legendItem: {
    display: 'flex',
    alignItems: 'center',
    gap: '4px',
  },
  tableSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  tableHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
  },
  tableTitle: {
    fontSize: '13px',
    fontWeight: 600,
  },
  tableCount: {
    fontSize: '12px',
    color: '#7A8BA7',
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
  code: {
    fontSize: '12px',
    fontFamily: 'monospace',
    color: '#7A8BA7',
  },
  name: {
    fontWeight: 600,
    marginRight: '6px',
  },
  brokenBadge: {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '11px',
    fontWeight: 600,
    background: 'rgba(255,184,77,0.2)',
    color: '#FFB84D',
    border: '1px solid rgba(255,184,77,0.4)',
    animation: 'blink 1s infinite',
  },
  boardBadge: {
    display: 'inline-block',
    padding: '1px 6px',
    borderRadius: '3px',
    fontSize: '11px',
    fontWeight: 600,
    background: 'rgba(255,107,107,0.2)',
    color: '#FF6B6B',
  },
}

export default LimitMonitor
