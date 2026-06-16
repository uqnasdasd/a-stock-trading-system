import React from 'react'

interface IndexData {
  code: string
  name: string
  price: number
  change_pct: number
  up_down: string
}

interface Props {
  data?: IndexData[]
  isLoading?: boolean
}

const MarketIndices: React.FC<Props> = ({ data, isLoading }) => {
  if (isLoading && !data) {
    return (
      <div style={styles.container}>
        <div style={styles.loading}>正在获取大盘指数...</div>
      </div>
    )
  }

  if (!data || data.length === 0) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>暂无指数数据</div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {data.map((idx) => {
        const isUp = idx.change_pct > 0
        const color = isUp ? '#00D4AA' : idx.change_pct < 0 ? '#FF6B6B' : '#7A8BA7'
        return (
          <div key={idx.code} style={styles.card}>
            <div style={styles.name}>{idx.name}</div>
            <div style={{ ...styles.price, color }}>
              {idx.price?.toFixed(2) ?? '--'}
            </div>
            <div style={{ ...styles.change, color }}>
              {isUp ? '+' : ''}{idx.change_pct?.toFixed(2) ?? '--'}%
            </div>
          </div>
        )
      })}
    </div>
  )
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    gap: '12px',
    padding: '12px 24px',
    background: '#131B2E',
    borderBottom: '1px solid #243050',
    overflowX: 'auto',
    alignItems: 'center',
  },
  loading: {
    color: '#FFB84D',
    fontSize: '13px',
    padding: '8px 0',
  },
  empty: {
    color: '#7A8BA7',
    fontSize: '13px',
    padding: '8px 0',
  },
  card: {
    minWidth: '140px',
    padding: '12px 16px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  name: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  price: {
    fontSize: '20px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  change: {
    fontSize: '13px',
    fontWeight: 600,
    marginTop: '2px',
  },
}

export default MarketIndices
