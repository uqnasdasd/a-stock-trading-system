import React, { useRef, useEffect } from 'react'

interface SectorStrength {
  sector_name: string
  avg_change_pct: number
  up_count: number
  down_count: number
  limit_up_count: number
  score: number
}

interface LeaderScore {
  code: string
  name: string
  sector: string
  change_pct: number
  score: number
  score_reason: string
}

interface Emotion {
  level: string
  score: number
  up_count: number
  down_count: number
  limit_up: number
  limit_down: number
}

interface AuctionVolume {
  code: string
  name: string
  minutes: { time: string; volume: number }[]
}

interface Props {
  data?: {
    sector_strengths?: SectorStrength[]
    leader_scores?: LeaderScore[]
    emotion?: Emotion
    candidates?: any[]
    auction_volumes?: AuctionVolume[]
    error?: string
  }
}

const AuctionPanel: React.FC<Props> = ({ data }) => {
  const sectors = data?.sector_strengths || []
  const leaders = data?.leader_scores || []
  const emotion = data?.emotion || { level: '平稳', score: 50, up_count: 0, down_count: 0, limit_up: 0, limit_down: 0 }
  const candidates = data?.candidates || []
  const auctionVolumes = data?.auction_volumes || []

  const getEmotionColor = (level: string) => {
    const map: Record<string, string> = {
      '火爆': '#FF6B6B',
      '活跃': '#FFB84D',
      '平稳': '#00D4AA',
      '低迷': '#7A8BA7',
      '恐慌': '#FF6B6B',
    }
    return map[level] || '#7A8BA7'
  }

  if (data?.error) {
    return (
      <div style={styles.container}>
        <div style={styles.empty}>
          <div style={styles.emptyIcon}>📡</div>
          <div style={styles.emptyText}>数据获取中...</div>
          <div style={styles.emptySub}>正在连接新浪财经API</div>
        </div>
      </div>
    )
  }

  return (
    <div style={styles.container}>
      {/* 情绪晴雨表 */}
      <div style={styles.emotionCard}>
        <div style={styles.emotionLabel}>市场情绪</div>
        <div style={{ ...styles.emotionValue, color: getEmotionColor(emotion.level) }}>{emotion.level}</div>
        <div style={styles.emotionScore}>评分: {emotion.score}</div>
        <div style={styles.emotionDetail}>
          涨{emotion.up_count} / 跌{emotion.down_count} | 涨停{emotion.limit_up} / 跌停{emotion.limit_down}
        </div>
      </div>

      {/* 竞价量能 */}
      <h3 style={styles.sectionTitle}>竞价量能 (9:15-9:25)</h3>
      <div style={styles.auctionVolumeContainer}>
        {auctionVolumes.length === 0 ? (
          <div style={styles.noData}>暂无竞价量能数据...</div>
        ) : (
          auctionVolumes.map((item) => (
            <AuctionVolumeBar key={item.code} item={item} />
          ))
        )}
      </div>

      {/* 板块强度 */}
      <h3 style={styles.sectionTitle}>板块强度 TOP5</h3>
      <div style={styles.tableContainer}>
        {sectors.length === 0 ? (
          <div style={styles.noData}>暂无板块数据，等待实时数据推送...</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>板块</th>
                <th style={styles.th}>平均涨幅</th>
                <th style={styles.th}>涨跌家数</th>
                <th style={styles.th}>涨停</th>
                <th style={styles.th}>强度分</th>
              </tr>
            </thead>
            <tbody>
              {sectors.map((s) => (
                <tr key={s.sector_name}>
                  <td style={styles.td}>{s.sector_name}</td>
                  <td style={{ ...styles.td, color: s.avg_change_pct > 0 ? '#00D4AA' : '#FF6B6B' }}>
                    {s.avg_change_pct > 0 ? '+' : ''}{s.avg_change_pct}%
                  </td>
                  <td style={styles.td}>{s.up_count}/{s.down_count}</td>
                  <td style={styles.td}>{s.limit_up_count}</td>
                  <td style={styles.td}>
                    <span style={scoreBadgeStyle(s.score)}>{s.score}</span>
                  </td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 龙头评分 */}
      <h3 style={styles.sectionTitle}>龙头竞价评分</h3>
      <div style={styles.tableContainer}>
        {leaders.length === 0 ? (
          <div style={styles.noData}>暂无龙头数据...</div>
        ) : (
          <table style={styles.table}>
            <thead>
              <tr>
                <th style={styles.th}>股票</th>
                <th style={styles.th}>板块</th>
                <th style={styles.th}>涨幅</th>
                <th style={styles.th}>评分</th>
                <th style={styles.th}>理由</th>
              </tr>
            </thead>
            <tbody>
              {leaders.map((l) => (
                <tr key={l.code}>
                  <td style={styles.td}>{l.name}({l.code})</td>
                  <td style={styles.td}>{l.sector}</td>
                  <td style={{ ...styles.td, color: l.change_pct > 0 ? '#00D4AA' : '#FF6B6B' }}>
                    {l.change_pct > 0 ? '+' : ''}{l.change_pct}%
                  </td>
                  <td style={styles.td}>
                    <span style={scoreBadgeStyle(l.score * 10)}>{l.score}/10</span>
                  </td>
                  <td style={{ ...styles.td, fontSize: '12px', color: '#7A8BA7' }}>{l.score_reason}</td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      {/* 潜力标的 */}
      {candidates.length > 0 && (
        <>
          <h3 style={styles.sectionTitle}>潜力标的</h3>
          <div style={styles.candidateList}>
            {candidates.map((c, i) => (
              <div key={c.code} style={styles.candidateCard}>
                <div style={styles.candidateName}>{i + 1}. {c.name}({c.code})</div>
                <div style={styles.candidateInfo}>
                  <span style={styles.candidateSector}>{c.sector}</span>
                  <span style={{ color: c.change_pct > 0 ? '#00D4AA' : '#FF6B6B' }}>
                    {c.change_pct > 0 ? '+' : ''}{c.change_pct}%
                  </span>
                  <span style={scoreBadgeStyle(c.score * 10)}>评分{c.score}</span>
                </div>
                <div style={{ fontSize: '12px', color: '#7A8BA7', marginTop: '4px' }}>{c.reason}</div>
              </div>
            ))}
          </div>
        </>
      )}
    </div>
  )
}

const AuctionVolumeBar: React.FC<{ item: AuctionVolume }> = ({ item }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null)

  useEffect(() => {
    if (!canvasRef.current || item.minutes.length === 0) return
    const canvas = canvasRef.current
    const ctx = canvas.getContext('2d')
    if (!ctx) return

    const dpr = window.devicePixelRatio || 1
    const width = canvas.clientWidth
    const height = canvas.clientHeight
    canvas.width = width * dpr
    canvas.height = height * dpr
    ctx.scale(dpr, dpr)

    const padding = { top: 4, bottom: 16, left: 4, right: 4 }
    const chartW = width - padding.left - padding.right
    const chartH = height - padding.top - padding.bottom

    const volumes = item.minutes.map(m => m.volume)
    const maxVolume = Math.max(...volumes, 1)
    const barGap = chartW / item.minutes.length
    const barW = Math.max(2, barGap * 0.6)

    ctx.clearRect(0, 0, width, height)

    item.minutes.forEach((m, i) => {
      const x = padding.left + i * barGap + barGap / 2
      const barH = (m.volume / maxVolume) * chartH
      const y = padding.top + chartH - barH

      const isUp = i > 0 ? m.volume >= item.minutes[i - 1].volume : true
      ctx.fillStyle = isUp ? 'rgba(0,212,170,0.7)' : 'rgba(255,107,107,0.7)'
      ctx.fillRect(x - barW / 2, y, barW, barH)
    })

    // 时间标签
    ctx.fillStyle = '#5A6B87'
    ctx.font = '9px monospace'
    ctx.textAlign = 'center'
    const step = Math.max(1, Math.ceil(item.minutes.length / 6))
    for (let i = 0; i < item.minutes.length; i += step) {
      const x = padding.left + i * barGap + barGap / 2
      ctx.fillText(item.minutes[i].time, x, height - 4)
    }
  }, [item])

  return (
    <div style={styles.volumeCard}>
      <div style={styles.volumeHeader}>
        <span style={styles.volumeName}>{item.name}</span>
        <span style={styles.volumeCode}>{item.code}</span>
      </div>
      <canvas ref={canvasRef} style={styles.volumeCanvas} />
    </div>
  )
}

const scoreBadgeStyle = (score: number): React.CSSProperties => ({
  display: 'inline-block',
  padding: '2px 8px',
  borderRadius: '4px',
  fontSize: '12px',
  fontWeight: 600,
  background: score >= 70 ? 'rgba(0,212,170,0.2)' : score >= 40 ? 'rgba(255,184,77,0.2)' : 'rgba(255,107,107,0.2)',
  color: score >= 70 ? '#00D4AA' : score >= 40 ? '#FFB84D' : '#FF6B6B',
})

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '16px',
  },
  empty: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#7A8BA7',
    padding: '40px',
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
  emotionCard: {
    padding: '16px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
    textAlign: 'center',
  },
  emotionLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '4px',
  },
  emotionValue: {
    fontSize: '28px',
    fontWeight: 700,
  },
  emotionScore: {
    fontSize: '14px',
    color: '#E8ECF4',
    marginTop: '4px',
  },
  emotionDetail: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginTop: '8px',
  },
  sectionTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#00D4AA',
    margin: '8px 0 4px 0',
    paddingLeft: '8px',
    borderLeft: '3px solid #00D4AA',
  },
  auctionVolumeContainer: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(240px, 1fr))',
    gap: '12px',
  },
  volumeCard: {
    padding: '10px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  volumeHeader: {
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    marginBottom: '6px',
  },
  volumeName: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#E8ECF4',
  },
  volumeCode: {
    fontSize: '11px',
    color: '#7A8BA7',
    fontFamily: 'monospace',
  },
  volumeCanvas: {
    width: '100%',
    height: '80px',
    display: 'block',
  },
  tableContainer: {
    overflow: 'auto',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  noData: {
    padding: '20px',
    textAlign: 'center',
    color: '#5A6B87',
    fontSize: '13px',
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
    padding: '8px 12px',
    borderBottom: '1px solid #243050',
    color: '#E8ECF4',
    whiteSpace: 'nowrap',
  },
  candidateList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  candidateCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  candidateName: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#E8ECF4',
  },
  candidateInfo: {
    display: 'flex',
    gap: '12px',
    marginTop: '4px',
    fontSize: '13px',
  },
  candidateSector: {
    color: '#7A8BA7',
  },
}

export default AuctionPanel
