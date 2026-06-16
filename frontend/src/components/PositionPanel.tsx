import React from 'react'

interface Position {
  code: string
  name: string
  buy_price: number
  current_price: number
  volume: number
  profit_pct: number
  market_value: number
}

interface Props {
  data?: {
    count?: number
    total_value?: number
    total_profit_pct?: number
    positions?: Position[]
  }
}

const PositionPanel: React.FC<Props> = ({ data }) => {
  const positions = data?.positions || []
  const totalValue = data?.total_value || 0
  const totalProfit = data?.total_profit_pct || 0

  return (
    <div style={styles.container}>
      {/* 汇总 */}
      <div style={styles.summary}>
        <div style={styles.summaryItem}>
          <div style={styles.summaryLabel}>持仓数量</div>
          <div style={styles.summaryValue}>{positions.length}只</div>
        </div>
        <div style={styles.summaryItem}>
          <div style={styles.summaryLabel}>总市值</div>
          <div style={styles.summaryValue}>¥{totalValue.toFixed(2)}</div>
        </div>
        <div style={styles.summaryItem}>
          <div style={styles.summaryLabel}>总盈亏</div>
          <div style={{ ...styles.summaryValue, color: totalProfit >= 0 ? '#00D4AA' : '#FF6B6B' }}>
            {totalProfit >= 0 ? '+' : ''}{totalProfit.toFixed(2)}%
          </div>
        </div>
      </div>

      {/* 持仓列表 */}
      <div style={styles.tableContainer}>
        <table style={styles.table}>
          <thead>
            <tr>
              <th style={styles.th}>股票</th>
              <th style={styles.th}>买入价</th>
              <th style={styles.th}>现价</th>
              <th style={styles.th}>盈亏</th>
              <th style={styles.th}>市值</th>
              <th style={styles.th}>信号</th>
            </tr>
          </thead>
          <tbody>
            {positions.length === 0 ? (
              <tr>
                <td colSpan={6} style={{ ...styles.td, textAlign: 'center', color: '#7A8BA7', padding: '40px' }}>
                  暂无持仓
                </td>
              </tr>
            ) : (
              positions.map((p) => (
                <tr key={p.code}>
                  <td style={styles.td}>
                    <div style={{ fontWeight: 600 }}>{p.name}</div>
                    <div style={{ fontSize: '12px', color: '#7A8BA7' }}>{p.code}</div>
                  </td>
                  <td style={styles.td}>¥{p.buy_price.toFixed(2)}</td>
                  <td style={styles.td}>¥{p.current_price.toFixed(2)}</td>
                  <td style={{ ...styles.td, color: p.profit_pct >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                    {p.profit_pct >= 0 ? '+' : ''}{p.profit_pct.toFixed(2)}%
                  </td>
                  <td style={styles.td}>¥{p.market_value.toFixed(2)}</td>
                  <td style={styles.td}>
                    {p.profit_pct >= 5 ? (
                      <span style={styles.badge('#FFB84D')}>止盈</span>
                    ) : p.profit_pct <= -3 ? (
                      <span style={styles.badge('#FF6B6B')}>止损</span>
                    ) : (
                      <span style={styles.badge('#00D4AA')}>持仓</span>
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

const styles: Record<string, any> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  summary: {
    display: 'flex',
    gap: '16px',
  },
  summaryItem: {
    flex: 1,
    padding: '16px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
    textAlign: 'center' as const,
  },
  summaryLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  summaryValue: {
    fontSize: '20px',
    fontWeight: 700,
    color: '#E8ECF4',
    fontFamily: 'monospace',
  },
  tableContainer: {
    overflow: 'auto',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  table: {
    width: '100%',
    borderCollapse: 'collapse' as const,
    fontSize: '13px',
  },
  th: {
    background: '#1A2540',
    color: '#00D4AA',
    fontWeight: 600,
    textAlign: 'left' as const,
    padding: '10px 12px',
    borderBottom: '2px solid #00D4AA',
    whiteSpace: 'nowrap' as const,
  },
  td: {
    padding: '10px 12px',
    borderBottom: '1px solid #243050',
    color: '#E8ECF4',
  },
  badge: (color: string) => ({
    display: 'inline-block',
    padding: '2px 8px',
    borderRadius: '4px',
    fontSize: '12px',
    fontWeight: 600,
    background: color + '33',
    color: color,
  }),
}

export default PositionPanel
