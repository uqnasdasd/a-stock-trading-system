import React, { useState, useEffect, useCallback } from 'react'

interface LeaderStock {
  code: string
  name: string
  change_pct: number
}

interface ConceptItem {
  name: string
  change_pct: number
  leader_stocks: LeaderStock[]
}

const ConceptPanel: React.FC = () => {
  const [concepts, setConcepts] = useState<ConceptItem[]>([])
  const [loading, setLoading] = useState(false)
  const [lastUpdate, setLastUpdate] = useState<string>('')

  const fetchConcepts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/concept/hot')
      const json = await res.json()
      if (json.data) {
        setConcepts(json.data)
      }
      setLastUpdate(new Date().toLocaleTimeString('zh-CN', { hour12: false }))
    } catch (e) {
      console.error('概念板块获取失败:', e)
    } finally {
      setLoading(false)
    }
  }, [])

  useEffect(() => {
    fetchConcepts()
    const timer = setInterval(fetchConcepts, 30000)
    return () => clearInterval(timer)
  }, [fetchConcepts])

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>热点概念板块</h3>
        <div style={styles.headerRight}>
          {loading && <span style={styles.loadingDot}>刷新中</span>}
          {lastUpdate && <span style={styles.lastUpdate}>{lastUpdate}</span>}
        </div>
      </div>

      {concepts.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyText}>暂无概念板块数据</div>
          <div style={styles.emptySub}>等待数据推送...</div>
        </div>
      ) : (
        <div style={styles.grid}>
          {concepts.map((concept) => {
            const isUp = concept.change_pct >= 0
            const color = isUp ? '#00D4AA' : '#FF6B6B'
            return (
              <div key={concept.name} style={styles.card}>
                <div style={styles.cardHeader}>
                  <span style={styles.conceptName}>{concept.name}</span>
                  <span style={{ ...styles.changePct, color }}>
                    {isUp ? '+' : ''}{concept.change_pct.toFixed(2)}%
                  </span>
                </div>
                <div style={styles.leaderList}>
                  {concept.leader_stocks.map((stock) => {
                    const stockColor = stock.change_pct >= 0 ? '#00D4AA' : '#FF6B6B'
                    return (
                      <div key={stock.code} style={styles.leaderItem}>
                        <span style={styles.leaderName}>{stock.name}</span>
                        <span style={{ ...styles.leaderCode, fontFamily: 'monospace' }}>{stock.code}</span>
                        <span style={{ color: stockColor, fontWeight: 600, fontFamily: 'monospace' }}>
                          {stock.change_pct >= 0 ? '+' : ''}{stock.change_pct.toFixed(2)}%
                        </span>
                      </div>
                    )
                  })}
                </div>
              </div>
            )
          })}
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
  grid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(280px, 1fr))',
    gap: '12px',
  },
  card: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
    paddingBottom: '8px',
    borderBottom: '1px solid #243050',
  },
  conceptName: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#E8ECF4',
  },
  changePct: {
    fontSize: '15px',
    fontWeight: 700,
    fontFamily: 'monospace',
  },
  leaderList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '6px',
  },
  leaderItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    fontSize: '13px',
  },
  leaderName: {
    color: '#E8ECF4',
    minWidth: '60px',
  },
  leaderCode: {
    color: '#7A8BA7',
    fontSize: '11px',
    flex: 1,
    textAlign: 'center',
  },
}

export default ConceptPanel
