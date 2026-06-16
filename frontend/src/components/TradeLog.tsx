import React, { useState, useEffect } from 'react'

interface TradeRecord {
  id: string
  timestamp: string
  code: string
  name: string
  action: string       // 'buy' | 'sell'
  price: number
  volume: number
  reason: string
  profit_pct?: number
}

const TradeLog: React.FC = () => {
  const [records, setRecords] = useState<TradeRecord[]>([])
  const [loading, setLoading] = useState(false)

  const fetchLogs = async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/trade/log')
      const json = await res.json()
      if (json.records) {
        setRecords(json.records)
      }
    } catch (e) {
      console.error('交易日志获取失败:', e)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchLogs()
  }, [])

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    return d.toLocaleString('zh-CN', {
      month: '2-digit',
      day: '2-digit',
      hour: '2-digit',
      minute: '2-digit',
      second: '2-digit',
      hour12: false,
    })
  }

  const exportCSV = () => {
    if (records.length === 0) return
    const headers = ['时间', '代码', '名称', '操作', '价格', '数量', '盈亏', '原因']
    const rows = records.map(r => [
      r.timestamp,
      r.code,
      r.name,
      r.action === 'buy' ? '买入' : '卖出',
      r.price.toFixed(2),
      String(r.volume),
      r.profit_pct !== undefined ? `${r.profit_pct >= 0 ? '+' : ''}${r.profit_pct.toFixed(2)}%` : '--',
      r.reason,
    ])
    const csv = [headers.join(','), ...rows.map(row => row.map(cell => `"${String(cell).replace(/"/g, '""')}"`).join(','))].join('\n')
    const blob = new Blob(['\uFEFF' + csv], { type: 'text/csv;charset=utf-8;' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `交易日志_${new Date().toISOString().slice(0, 10)}.csv`
    document.body.appendChild(a)
    a.click()
    document.body.removeChild(a)
    URL.revokeObjectURL(url)
  }

  const getActionStyle = (action: string): React.CSSProperties => {
    if (action === 'buy') {
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

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>交易日志</h3>
        <div style={styles.headerRight}>
          <button style={styles.exportBtn} onClick={exportCSV} disabled={records.length === 0}>
            导出CSV
          </button>
          <button style={styles.refreshBtn} onClick={fetchLogs} disabled={loading}>
            {loading ? '加载中...' : '刷新'}
          </button>
        </div>
      </div>

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
              <th style={styles.th}>原因</th>
            </tr>
          </thead>
          <tbody>
            {records.length === 0 ? (
              <tr>
                <td colSpan={8} style={{ ...styles.td, textAlign: 'center', color: '#5A6B87', padding: '40px' }}>
                  暂无交易记录
                </td>
              </tr>
            ) : (
              records.map((record) => (
                <tr key={record.id} style={styles.tr}>
                  <td style={{ ...styles.td, fontFamily: 'monospace', fontSize: '12px', color: '#7A8BA7' }}>
                    {formatTime(record.timestamp)}
                  </td>
                  <td style={{ ...styles.td, fontFamily: 'monospace' }}>{record.code}</td>
                  <td style={{ ...styles.td, fontWeight: 600 }}>{record.name}</td>
                  <td style={styles.td}>
                    <span style={getActionStyle(record.action)}>
                      {record.action === 'buy' ? '买入' : '卖出'}
                    </span>
                  </td>
                  <td style={{ ...styles.td, fontFamily: 'monospace', fontWeight: 600 }}>
                    {record.price?.toFixed(2)}
                  </td>
                  <td style={{ ...styles.td, fontFamily: 'monospace' }}>
                    {record.volume}
                  </td>
                  <td style={styles.td}>
                    {record.profit_pct !== undefined && record.profit_pct !== null ? (
                      <span style={{
                        color: record.profit_pct >= 0 ? '#00D4AA' : '#FF6B6B',
                        fontWeight: 600,
                        fontFamily: 'monospace',
                      }}>
                        {record.profit_pct >= 0 ? '+' : ''}{record.profit_pct.toFixed(2)}%
                      </span>
                    ) : (
                      <span style={{ color: '#5A6B87' }}>--</span>
                    )}
                  </td>
                  <td style={{ ...styles.td, fontSize: '12px', color: '#7A8BA7', maxWidth: '160px', overflow: 'hidden', textOverflow: 'ellipsis' }}>
                    {record.reason}
                  </td>
                </tr>
              ))
            )}
          </tbody>
        </table>
      </div>

      {records.length > 0 && (
        <div style={styles.footer}>
          共 {records.length} 条交易记录
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
  footer: {
    fontSize: '11px',
    color: '#5A6B87',
    textAlign: 'right',
  },
}

export default TradeLog
