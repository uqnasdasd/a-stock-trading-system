import React, { useState } from 'react'

interface RiskData {
  total_position_pct?: number
  daily_profit_pct?: number
  weekly_profit_pct?: number
  daily_trade_count?: number
  weekly_trade_count?: number
  is_locked?: boolean
  lock_reason?: string
  total_capital?: number
  used_capital?: number
  available_capital?: number
}

interface Props {
  data?: RiskData
}

const RiskPanel: React.FC<Props> = ({ data }) => {
  const risk = data || {
    total_position_pct: 0,
    daily_profit_pct: 0,
    weekly_profit_pct: 0,
    daily_trade_count: 0,
    weekly_trade_count: 0,
    is_locked: false,
    lock_reason: '',
    total_capital: 0,
    used_capital: 0,
    available_capital: 0,
  }

  const [capitalInput, setCapitalInput] = useState('')
  const [capitalSaving, setCapitalSaving] = useState(false)
  const [capitalSaved, setCapitalSaved] = useState(false)

  const positionPct = (risk.total_position_pct || 0) * 100
  const dailyProfit = (risk.daily_profit_pct || 0) * 100
  const weeklyProfit = (risk.weekly_profit_pct || 0) * 100
  const totalCapital = risk.total_capital || 0
  const usedCapital = risk.used_capital || 0
  const availableCapital = risk.available_capital || 0

  // 可买股数计算：可用资金 / (股价 * 100) 取整（A股最少100股）
  const calcBuyableShares = (price: number) => {
    if (!price || price <= 0 || availableCapital <= 0) return 0
    return Math.floor(availableCapital / (price * 100)) * 100
  }

  const saveCapital = async () => {
    const amount = parseFloat(capitalInput)
    if (isNaN(amount) || amount <= 0) return

    setCapitalSaving(true)
    setCapitalSaved(false)
    try {
      const res = await fetch('/api/risk/capital', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ total_capital: amount }),
      })
      const json = await res.json()
      if (json.success !== false) {
        setCapitalSaved(true)
        setCapitalInput('')
        setTimeout(() => setCapitalSaved(false), 3000)
      }
    } catch (e) {
      console.error('保存资金失败:', e)
    } finally {
      setCapitalSaving(false)
    }
  }

  return (
    <div style={styles.container}>
      <h3 style={styles.title}>风控中心</h3>

      {/* 锁定状态 */}
      {risk.is_locked && (
        <div style={styles.lockAlert}>
          <div style={styles.lockTitle}>交易已锁定</div>
          <div style={styles.lockReason}>{risk.lock_reason}</div>
        </div>
      )}

      {/* 资金管理 */}
      <div style={styles.capitalCard}>
        <div style={styles.capitalHeader}>
          <span style={styles.capitalLabel}>资金管理</span>
          <span style={styles.capitalStatus}>
            {totalCapital > 0 ? '已设置' : '未设置'}
          </span>
        </div>

        <div style={styles.capitalInputRow}>
          <input
            style={styles.capitalInput}
            type="number"
            placeholder="输入总资金（元）"
            value={capitalInput}
            onChange={(e) => setCapitalInput(e.target.value)}
            onKeyDown={(e) => e.key === 'Enter' && saveCapital()}
          />
          <button
            style={{ ...styles.capitalBtn, opacity: capitalSaving ? 0.6 : 1 }}
            onClick={saveCapital}
            disabled={capitalSaving}
          >
            {capitalSaving ? '保存中...' : '设置'}
          </button>
        </div>
        {capitalSaved && (
          <div style={styles.capitalSaved}>资金设置成功</div>
        )}

        {totalCapital > 0 && (
          <div style={styles.capitalInfo}>
            <div style={styles.capitalRow}>
              <span style={styles.capitalInfoLabel}>总资金</span>
              <span style={styles.capitalValue}>{totalCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</span>
            </div>
            <div style={styles.capitalRow}>
              <span style={styles.capitalInfoLabel}>已用资金</span>
              <span style={{ ...styles.capitalValue, color: '#FFB84D' }}>{usedCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</span>
            </div>
            <div style={styles.capitalRow}>
              <span style={styles.capitalInfoLabel}>可用资金</span>
              <span style={{ ...styles.capitalValue, color: '#00D4AA' }}>{availableCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}</span>
            </div>
            <div style={styles.capitalBar}>
              <div style={styles.capitalBarBg}>
                <div style={{
                  ...styles.capitalBarFill,
                  width: `${totalCapital > 0 ? (usedCapital / totalCapital * 100) : 0}%`,
                  background: (usedCapital / totalCapital) >= 0.5 ? '#FF6B6B' : '#00D4AA',
                }} />
              </div>
              <span style={styles.capitalBarText}>
                {totalCapital > 0 ? ((usedCapital / totalCapital) * 100).toFixed(1) : 0}% 已使用
              </span>
            </div>

            {/* 可买股数参考 */}
            <div style={styles.buyableSection}>
              <div style={styles.buyableLabel}>可买股数参考（按100股整数倍）</div>
              {[10, 20, 50, 100].map(price => (
                <div key={price} style={styles.buyableRow}>
                  <span style={styles.buyablePrice}>{price.toFixed(2)}元</span>
                  <span style={styles.buyableCount}>{calcBuyableShares(price)}股</span>
                </div>
              ))}
            </div>
          </div>
        )}
      </div>

      {/* 仓位 */}
      <div style={styles.metricCard}>
        <div style={styles.metricLabel}>总仓位</div>
        <div style={styles.metricBar}>
          <div style={styles.metricFill(positionPct, 50)} />
        </div>
        <div style={styles.metricValue(positionPct >= 50 ? '#FF6B6B' : '#00D4AA')}>
          {positionPct.toFixed(1)}% / 50%
        </div>
      </div>

      {/* 当日盈亏 */}
      <div style={styles.metricCard}>
        <div style={styles.metricLabel}>当日盈亏</div>
        <div style={styles.metricBar}>
          <div style={styles.profitFill(dailyProfit, 3)} />
        </div>
        <div style={styles.metricValue(dailyProfit >= 0 ? '#00D4AA' : '#FF6B6B')}>
          {dailyProfit >= 0 ? '+' : ''}{dailyProfit.toFixed(2)}%
        </div>
        {dailyProfit <= -3 && (
          <div style={styles.limitAlert}>已达单日回撤上限3%</div>
        )}
      </div>

      {/* 本周盈亏 */}
      <div style={styles.metricCard}>
        <div style={styles.metricLabel}>本周盈亏</div>
        <div style={styles.metricValue(weeklyProfit >= 0 ? '#00D4AA' : '#FF6B6B')}>
          {weeklyProfit >= 0 ? '+' : ''}{weeklyProfit.toFixed(2)}%
        </div>
        {weeklyProfit <= -5 && (
          <div style={styles.limitAlert}>已达周度回撤上限5%</div>
        )}
      </div>

      {/* 交易次数 */}
      <div style={styles.metricCard}>
        <div style={styles.metricLabel}>交易次数</div>
        <div style={styles.tradeCount}>
          <div>
            <span style={styles.countValue(risk.daily_trade_count || 0, 2)}>{risk.daily_trade_count || 0}</span>
            <span style={styles.countLabel}>/2 今日</span>
          </div>
          <div>
            <span style={styles.countValue(risk.weekly_trade_count || 0, 5)}>{risk.weekly_trade_count || 0}</span>
            <span style={styles.countLabel}>/5 本周</span>
          </div>
        </div>
      </div>

      {/* 风控规则 */}
      <div style={styles.rulesCard}>
        <div style={styles.rulesTitle}>风控规则</div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#00D4AA')} />
          {'单票仓位 \u2264 10%'}
        </div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#00D4AA')} />
          {'总仓位 \u2264 50%'}
        </div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#FF6B6B')} />
          {'止损线 -2%~-3%'}
        </div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#FFB84D')} />
          {'止盈 4%~6%'}
        </div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#FF6B6B')} />
          {'单日回撤 \u2265 3% 停手'}
        </div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#FF6B6B')} />
          {'周度回撤 \u2265 5% 暂停'}
        </div>
        <div style={styles.ruleItem}>
          <span style={styles.ruleDot('#7A8BA7')} />
          非涨停股不过夜
        </div>
      </div>
    </div>
  )
}

const styles: Record<string, any> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
    padding: '16px',
    background: '#131B2E',
    borderRadius: '8px',
    border: '1px solid #243050',
    height: '100%',
    overflow: 'auto',
  },
  title: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#00D4AA',
    margin: 0,
    paddingBottom: '8px',
    borderBottom: '1px solid #243050',
  },
  lockAlert: {
    padding: '12px',
    background: 'rgba(255,107,107,0.15)',
    borderRadius: '6px',
    border: '1px solid rgba(255,107,107,0.3)',
  },
  lockTitle: {
    fontSize: '14px',
    fontWeight: 600,
    color: '#FF6B6B',
  },
  lockReason: {
    fontSize: '12px',
    color: '#E8ECF4',
    marginTop: '4px',
  },
  capitalCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '6px',
  },
  capitalHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  capitalLabel: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#E8ECF4',
  },
  capitalStatus: {
    fontSize: '11px',
    color: '#7A8BA7',
  },
  capitalInputRow: {
    display: 'flex',
    gap: '6px',
    marginBottom: '6px',
  },
  capitalInput: {
    flex: 1,
    padding: '6px 10px',
    background: '#0B1120',
    border: '1px solid #243050',
    borderRadius: '4px',
    color: '#E8ECF4',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'monospace',
  },
  capitalBtn: {
    padding: '6px 14px',
    background: '#00D4AA',
    color: '#0B1120',
    border: 'none',
    borderRadius: '4px',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  capitalSaved: {
    fontSize: '11px',
    color: '#00D4AA',
    marginBottom: '4px',
  },
  capitalInfo: {
    marginTop: '8px',
  },
  capitalRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '4px 0',
  },
  capitalInfoLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
  },
  capitalValue: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#E8ECF4',
    fontFamily: 'monospace',
  },
  capitalBar: {
    marginTop: '6px',
  },
  capitalBarBg: {
    height: '6px',
    background: '#243050',
    borderRadius: '3px',
    overflow: 'hidden',
    marginBottom: '4px',
  },
  capitalBarFill: {
    height: '100%',
    borderRadius: '3px',
    transition: 'width 0.3s',
  },
  capitalBarText: {
    fontSize: '11px',
    color: '#5A6B87',
  },
  buyableSection: {
    marginTop: '10px',
    padding: '8px',
    background: '#0B1120',
    borderRadius: '4px',
    border: '1px solid #243050',
  },
  buyableLabel: {
    fontSize: '11px',
    color: '#7A8BA7',
    marginBottom: '6px',
  },
  buyableRow: {
    display: 'flex',
    justifyContent: 'space-between',
    padding: '3px 0',
  },
  buyablePrice: {
    fontSize: '12px',
    color: '#9AABBF',
    fontFamily: 'monospace',
  },
  buyableCount: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#00D4AA',
    fontFamily: 'monospace',
  },
  metricCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '6px',
  },
  metricLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginBottom: '6px',
  },
  metricBar: {
    height: '6px',
    background: '#243050',
    borderRadius: '3px',
    overflow: 'hidden',
    marginBottom: '6px',
  },
  metricFill: (pct: number, max: number) => ({
    height: '100%',
    width: `${Math.min(pct / max * 100, 100)}%`,
    background: pct >= max ? '#FF6B6B' : '#00D4AA',
    borderRadius: '3px',
    transition: 'width 0.3s',
  }),
  profitFill: (pct: number, max: number) => ({
    height: '100%',
    width: `${Math.min(Math.abs(pct) / max * 100, 100)}%`,
    background: pct >= 0 ? '#00D4AA' : '#FF6B6B',
    borderRadius: '3px',
    transition: 'width 0.3s',
  }),
  metricValue: (color: string) => ({
    fontSize: '18px',
    fontWeight: 700,
    color: color,
    fontFamily: 'monospace',
  }),
  limitAlert: {
    fontSize: '11px',
    color: '#FF6B6B',
    marginTop: '4px',
  },
  tradeCount: {
    display: 'flex',
    justifyContent: 'space-between',
  },
  countValue: (current: number, limit: number) => ({
    fontSize: '20px',
    fontWeight: 700,
    color: current >= limit ? '#FF6B6B' : '#E8ECF4',
    fontFamily: 'monospace',
  }),
  countLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
    marginLeft: '4px',
  },
  rulesCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '6px',
    marginTop: '4px',
  },
  rulesTitle: {
    fontSize: '12px',
    fontWeight: 600,
    color: '#7A8BA7',
    marginBottom: '8px',
  },
  ruleItem: {
    fontSize: '12px',
    color: '#E8ECF4',
    display: 'flex',
    alignItems: 'center',
    gap: '8px',
    padding: '4px 0',
  },
  ruleDot: (color: string) => ({
    width: '6px',
    height: '6px',
    borderRadius: '50%',
    background: color,
    flexShrink: 0,
  }),
}

export default RiskPanel
