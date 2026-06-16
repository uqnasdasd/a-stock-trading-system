import React, { useState, useEffect, useCallback } from 'react'

interface DeptInfo {
  name: string
  amount: number
}

interface DragonTigerItem {
  code: string
  name: string
  net_buy: number
  buy_depts: DeptInfo[]
  sell_depts: DeptInfo[]
  change_pct: number
  reason: string
}

const DragonTiger: React.FC = () => {
  const [items, setItems] = useState<DragonTigerItem[]>([])
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  const fetchData = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/dragon/today')
      const json = await res.json()
      if (json.data) {
        setItems(json.data)
      }
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    } catch (e) {
      console.error('龙虎榜获取失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchData()
    const timer = setInterval(fetchData, 30000)
    return () => clearInterval(timer)
  }, [fetchData])

  const formatAmount = (amount: number) => {
    if (Math.abs(amount) >= 100000000) return (amount / 100000000).toFixed(2) + '亿'
    if (Math.abs(amount) >= 10000) return (amount / 10000).toFixed(0) + '万'
    return amount.toString()
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>今日龙虎榜</h3>
        <div style={styles.headerRight}>
          {loading && <span style={styles.loadingDot}>刷新中</span>}
          {lastUpdate && <span style={styles.lastUpdate}>{lastUpdate}</span>}
        </div>
      </div>

      {items.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyText}>暂无龙虎榜数据</div>
          <div style={styles.emptySub}>等待数据推送...</div>
        </div>
      ) : (
        <div style={styles.tableContainer}>
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>股票</th>
                <th style={styles.th}>涨跌幅</th>
                <th style={styles.th}>净买入</th>
                <th style={styles.th}>买入营业部</th>
                <th style={styles.th}>卖出营业部</th>
                <th style={styles.th}>上榜原因</th>
              </tr>
            </thead>
            <tbody>
              {items.map((item) => {
                const color = item.change_pct >= 0 ? '#00D4AA' : '#FF6B6B'
                const netColor = item.net_buy >= 0 ? '#00D4AA' : '#FF6B6B'
                return (
                  <tr key={item.code}>
                    <td style={styles.td}>
                      <div style={styles.stockName}>{item.name}</div>
                      <div style={styles.stockCode}>{item.code}</div>
                    </td>
                    <td style={{ ...styles.td, color, fontWeight: 600, fontFamily: 'monospace' }}>
                      {item.change_pct >= 0 ? '+' : ''}{item.change_pct.toFixed(2)}%
                    </td>
                    <td style={{ ...styles.td, color: netColor, fontWeight: 600, fontFamily: 'monospace' }}>
                      {item.net_buy >= 0 ? '+' : ''}{formatAmount(item.net_buy)}
                    </td>
                    <td style={styles.td}>
                      <div style={styles.deptList}>
                        {item.buy_depts.map((d, i) => (
                          <div key={i} style={styles.deptItem}>
                            <span style={styles.deptName}>{d.name}</span>
                            <span style={{ ...styles.deptAmount, color: '#00D4AA' }}>+{formatAmount(d.amount)}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                    <td style={styles.td}>
                      <div style={styles.deptList}>
                        {item.sell_depts.map((d, i) => (
                          <div key={i} style={styles.deptItem}>
                            <span style={styles.deptName}>{d.name}</span>
                            <span style={{ ...styles.deptAmount, color: '#FF6B6B' }}>-{formatAmount(Math.abs(d.amount))}</span>
                          </div>
                        ))}
                      </div>
                    </td>
                    <td style={{ ...styles.td, fontSize: '12px', color: '#7A8BA7', maxWidth: '180px' }}>
                      {item.reason}
                    </td>
                  </tr>
                )
              })}
            </tbody>
          </table>
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
    padding: '10px 12px',
    borderBottom: '2px solid #00D4AA',
    whiteSpace: 'nowrap',
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #243050',
    color: '#E8ECF4',
    verticalAlign: 'top',
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
  deptList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
  },
  deptItem: {
    display: 'flex',
    justifyContent: 'space-between',
    gap: '8px',
    fontSize: '12px',
  },
  deptName: {
    color: '#E8ECF4',
    wordBreak: 'break-all',
    maxWidth: '140px',
  },
  deptAmount: {
    fontWeight: 600,
    fontFamily: 'monospace',
    whiteSpace: 'nowrap',
    flexShrink: 0,
  },
}

export default DragonTiger
