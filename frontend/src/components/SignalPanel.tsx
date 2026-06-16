import React from 'react'

interface Signal {
  id: string
  type: string
  level: string
  code: string
  name: string
  message: string
  trigger_price?: number
  trigger_condition: string
  suggested_action: string
  timestamp: string
  is_read: boolean
}

interface SignalPanelProps {
  data?: Signal[]
}

const SignalPanel: React.FC<SignalPanelProps> = ({ data }) => {
  const signals = data || []

  const getLevelColor = (level: string) => {
    switch (level) {
      case 'emergency': return { bg: '#3D1515', border: '#FF4444', text: '#FF6B6B' }
      case 'important': return { bg: '#3D1F0D', border: '#FF8800', text: '#FFAA44' }
      case 'normal': return { bg: '#3D320D', border: '#FFCC00', text: '#FFDD55' }
      default: return { bg: '#0F2744', border: '#00A8FF', text: '#44BBFF' }
    }
  }

  const getTypeLabel = (type: string) => {
    const map: Record<string, string> = {
      auction_buy: '竞价买点',
      open_confirm: '开盘确认',
      morning_breakout: '早盘突破',
      afternoon_stable: '尾盘稳健',
      stop_loss: '止损信号',
      take_profit: '止盈信号',
      position_hold: '持仓提示',
      position_sell: '清仓信号',
      risk_alert: '风控告警',
    }
    return map[type] || type
  }

  const getActionColor = (action: string) => {
    if (action.includes('买入') || action.includes('建仓')) return '#00D4AA'
    if (action.includes('卖出') || action.includes('清仓') || action.includes('止损')) return '#FF6B6B'
    if (action.includes('持仓') || action.includes('持有')) return '#FFCC00'
    return '#7A8BA7'
  }

  const formatTime = (ts: string) => {
    const d = new Date(ts)
    return d.toLocaleTimeString('zh-CN', { hour12: false })
  }

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>实时信号</h3>
        <span style={styles.count}>{signals.filter(s => !s.is_read).length} 条未读</span>
      </div>

      {signals.length === 0 ? (
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>📡</div>
          <div style={styles.emptyText}>暂无交易信号</div>
          <div style={styles.emptySub}>系统正在实时监控中...</div>
        </div>
      ) : (
        <div style={styles.list}>
          {signals.map((signal) => {
            const colors = getLevelColor(signal.level)
            return (
              <div
                key={signal.id}
                style={{
                  ...styles.card,
                  background: colors.bg,
                  borderLeft: `3px solid ${colors.border}`,
                  opacity: signal.is_read ? 0.6 : 1,
                }}
              >
                <div style={styles.cardHeader}>
                  <div style={styles.badgeRow}>
                    <span style={{ ...styles.levelBadge, color: colors.text, borderColor: colors.border }}>
                      {signal.level === 'emergency' ? '紧急' : signal.level === 'important' ? '重要' : signal.level === 'normal' ? '一般' : '信息'}
                    </span>
                    <span style={styles.typeBadge}>{getTypeLabel(signal.type)}</span>
                  </div>
                  <span style={styles.time}>{formatTime(signal.timestamp)}</span>
                </div>

                <div style={styles.stockRow}>
                  <span style={styles.code}>{signal.code}</span>
                  <span style={styles.name}>{signal.name}</span>
                  {signal.trigger_price && (
                    <span style={styles.price}>¥{signal.trigger_price.toFixed(2)}</span>
                  )}
                </div>

                <div style={styles.message}>{signal.message}</div>

                <div style={styles.footer}>
                  <span style={styles.condition}>触发: {signal.trigger_condition}</span>
                  <span style={{ ...styles.action, color: getActionColor(signal.suggested_action) }}>
                    {signal.suggested_action}
                  </span>
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
    height: '100%',
    display: 'flex',
    flexDirection: 'column',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '12px',
  },
  title: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  count: {
    fontSize: '12px',
    color: '#FF6B6B',
    fontWeight: 500,
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#7A8BA7',
  },
  emptyIcon: {
    fontSize: '36px',
    marginBottom: '12px',
    opacity: 0.5,
  },
  emptyText: {
    fontSize: '15px',
    marginBottom: '4px',
  },
  emptySub: {
    fontSize: '12px',
    opacity: 0.6,
  },
  list: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
    overflow: 'auto',
    flex: 1,
  },
  card: {
    padding: '12px',
    borderRadius: '6px',
    transition: 'opacity 0.2s',
  },
  cardHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  badgeRow: {
    display: 'flex',
    gap: '6px',
  },
  levelBadge: {
    fontSize: '11px',
    fontWeight: 600,
    padding: '2px 6px',
    borderRadius: '4px',
    border: '1px solid',
  },
  typeBadge: {
    fontSize: '11px',
    color: '#7A8BA7',
    background: '#1A2540',
    padding: '2px 6px',
    borderRadius: '4px',
  },
  time: {
    fontSize: '11px',
    color: '#5A6B87',
  },
  stockRow: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  code: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#E8ECF4',
    fontFamily: 'monospace',
  },
  name: {
    fontSize: '13px',
    color: '#9AABBF',
  },
  price: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
    marginLeft: 'auto',
  },
  message: {
    fontSize: '13px',
    color: '#B8C4D4',
    lineHeight: 1.5,
    marginBottom: '8px',
  },
  footer: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    paddingTop: '8px',
    borderTop: '1px solid rgba(255,255,255,0.06)',
  },
  condition: {
    fontSize: '11px',
    color: '#5A6B87',
  },
  action: {
    fontSize: '12px',
    fontWeight: 700,
  },
}

export default SignalPanel
