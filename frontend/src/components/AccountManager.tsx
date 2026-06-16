import React, { useState, useEffect, useCallback } from 'react'

interface Account {
  id: string
  name: string
  totalCapital: number
  usedCapital: number
  availableCapital: number
  positions: AccountPosition[]
  createdAt: string
}

interface AccountPosition {
  code: string
  name: string
  buyPrice: number
  currentPrice: number
  volume: number
  profitPct: number
  marketValue: number
}

const AccountManager: React.FC = () => {
  const [accounts, setAccounts] = useState<Account[]>([])
  const [activeAccountId, setActiveAccountId] = useState<string>('')
  const [loading, setLoading] = useState(false)
  const [showAddForm, setShowAddForm] = useState(false)
  const [newAccountName, setNewAccountName] = useState('')
  const [newAccountCapital, setNewAccountCapital] = useState('')
  const [saveSuccess, setSaveSuccess] = useState(false)

  const fetchAccounts = useCallback(async () => {
    setLoading(true)
    try {
      const res = await fetch('/api/accounts')
      if (res.ok) {
        const json = await res.json()
        if (json.accounts) {
          setAccounts(json.accounts)
          if (json.accounts.length > 0 && !activeAccountId) {
            setActiveAccountId(json.accounts[0].id)
          }
          return
        }
      }
    } catch (e) {
      console.warn('账户API调用失败，使用本地数据:', e)
    } finally {
      setLoading(false)
    }
    // 本地模拟数据
    const mockAccounts: Account[] = [
      {
        id: 'acc-1',
        name: '主账户',
        totalCapital: 500000,
        usedCapital: 180000,
        availableCapital: 320000,
        positions: [
          { code: '600519', name: '贵州茅台', buyPrice: 1680, currentPrice: 1725, volume: 100, profitPct: 2.68, marketValue: 172500 },
          { code: '300750', name: '宁德时代', buyPrice: 185, currentPrice: 178, volume: 500, profitPct: -3.78, marketValue: 89000 },
        ],
        createdAt: '2024-01-15T08:00:00Z',
      },
      {
        id: 'acc-2',
        name: '短线账户',
        totalCapital: 200000,
        usedCapital: 80000,
        availableCapital: 120000,
        positions: [
          { code: '002594', name: '比亚迪', buyPrice: 245, currentPrice: 258, volume: 200, profitPct: 5.31, marketValue: 51600 },
        ],
        createdAt: '2024-03-01T08:00:00Z',
      },
    ]
    setAccounts(mockAccounts)
    if (!activeAccountId) setActiveAccountId(mockAccounts[0].id)
  }, [activeAccountId])

  useEffect(() => {
    fetchAccounts()
  }, [fetchAccounts])

  const saveAccounts = async (updated: Account[]) => {
    try {
      await fetch('/api/accounts', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({ accounts: updated }),
      })
    } catch (e) {
      console.warn('保存账户到后端失败:', e)
    }
  }

  const addAccount = async () => {
    const name = newAccountName.trim()
    const capital = parseFloat(newAccountCapital)
    if (!name || isNaN(capital) || capital <= 0) return

    const newAccount: Account = {
      id: `acc-${Date.now()}`,
      name,
      totalCapital: capital,
      usedCapital: 0,
      availableCapital: capital,
      positions: [],
      createdAt: new Date().toISOString(),
    }

    const updated = [...accounts, newAccount]
    setAccounts(updated)
    setActiveAccountId(newAccount.id)
    setNewAccountName('')
    setNewAccountCapital('')
    setShowAddForm(false)
    await saveAccounts(updated)

    setSaveSuccess(true)
    setTimeout(() => setSaveSuccess(false), 2000)
  }

  const deleteAccount = async (id: string) => {
    const updated = accounts.filter(a => a.id !== id)
    setAccounts(updated)
    if (activeAccountId === id && updated.length > 0) {
      setActiveAccountId(updated[0].id)
    }
    await saveAccounts(updated)
  }

  const activeAccount = accounts.find(a => a.id === activeAccountId)

  const totalProfit = activeAccount
    ? ((activeAccount.usedCapital > 0
        ? activeAccount.positions.reduce((sum, p) => sum + (p.currentPrice - p.buyPrice) * p.volume, 0)
        : 0))
    : 0

  const totalProfitPct = activeAccount && activeAccount.usedCapital > 0
    ? (totalProfit / activeAccount.usedCapital) * 100
    : 0

  return (
    <div style={styles.container}>
      <div style={styles.header}>
        <h3 style={styles.title}>账户管理</h3>
        <button style={styles.addBtn} onClick={() => setShowAddForm(!showAddForm)}>
          {showAddForm ? '取消' : '+ 添加账户'}
        </button>
      </div>

      {saveSuccess && <div style={styles.saveSuccess}>账户保存成功</div>}

      {/* 添加账户表单 */}
      {showAddForm && (
        <div style={styles.formCard}>
          <div style={styles.formTitle}>新建账户</div>
          <div style={styles.formRow}>
            <div style={styles.formItem}>
              <label style={styles.formLabel}>账户名称</label>
              <input
                style={styles.formInput}
                placeholder="如：短线账户"
                value={newAccountName}
                onChange={e => setNewAccountName(e.target.value)}
              />
            </div>
            <div style={styles.formItem}>
              <label style={styles.formLabel}>总资金 (元)</label>
              <input
                style={styles.formInput}
                type="number"
                placeholder="100000"
                value={newAccountCapital}
                onChange={e => setNewAccountCapital(e.target.value)}
              />
            </div>
            <button style={styles.confirmBtn} onClick={addAccount}>确认添加</button>
          </div>
        </div>
      )}

      {/* 账户切换 */}
      {accounts.length > 0 && (
        <div style={styles.accountTabs}>
          {accounts.map(acc => (
            <button
              key={acc.id}
              style={{
                ...styles.accountTab,
                background: activeAccountId === acc.id ? '#00D4AA' : '#1A2540',
                color: activeAccountId === acc.id ? '#0B1120' : '#7A8BA7',
              }}
              onClick={() => setActiveAccountId(acc.id)}
            >
              <span style={styles.tabName}>{acc.name}</span>
              <span style={styles.tabCapital}>¥{(acc.totalCapital / 10000).toFixed(1)}万</span>
              {accounts.length > 1 && (
                <span
                  style={styles.tabClose}
                  onClick={(e) => {
                    e.stopPropagation()
                    if (confirm(`确定删除账户 "${acc.name}" 吗？`)) {
                      deleteAccount(acc.id)
                    }
                  }}
                >
                  ×
                </span>
              )}
            </button>
          ))}
        </div>
      )}

      {loading && accounts.length === 0 && (
        <div style={styles.empty}>加载中...</div>
      )}

      {!loading && accounts.length === 0 && (
        <div style={styles.empty}>
          <div style={styles.emptyText}>暂无交易账户</div>
          <div style={styles.emptySub}>点击右上角添加账户</div>
        </div>
      )}

      {/* 活跃账户详情 */}
      {activeAccount && (
        <div style={styles.detailSection}>
          {/* 资金概览 */}
          <div style={styles.overviewGrid}>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>总资金</div>
              <div style={styles.overviewValue}>
                ¥{activeAccount.totalCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>已用资金</div>
              <div style={{ ...styles.overviewValue, color: '#FFB84D' }}>
                ¥{activeAccount.usedCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>可用资金</div>
              <div style={{ ...styles.overviewValue, color: '#00D4AA' }}>
                ¥{activeAccount.availableCapital.toLocaleString('zh-CN', { minimumFractionDigits: 2 })}
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>持仓盈亏</div>
              <div style={{ ...styles.overviewValue, color: totalProfit >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {totalProfit >= 0 ? '+' : ''}{totalProfit.toFixed(2)}
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>盈亏比例</div>
              <div style={{ ...styles.overviewValue, color: totalProfitPct >= 0 ? '#00D4AA' : '#FF6B6B' }}>
                {totalProfitPct >= 0 ? '+' : ''}{totalProfitPct.toFixed(2)}%
              </div>
            </div>
            <div style={styles.overviewCard}>
              <div style={styles.overviewLabel}>仓位</div>
              <div style={styles.overviewValue}>
                {activeAccount.totalCapital > 0
                  ? ((activeAccount.usedCapital / activeAccount.totalCapital) * 100).toFixed(1)
                  : '0'}%
              </div>
            </div>
          </div>

          {/* 资金进度条 */}
          <div style={styles.capitalBarCard}>
            <div style={styles.capitalBarRow}>
              <span style={styles.capitalBarLabel}>资金使用率</span>
              <span style={styles.capitalBarText}>
                {activeAccount.totalCapital > 0
                  ? ((activeAccount.usedCapital / activeAccount.totalCapital) * 100).toFixed(1)
                  : 0}% / 50% 上限
              </span>
            </div>
            <div style={styles.capitalBarBg}>
              <div
                style={{
                  ...styles.capitalBarFill,
                  width: `${activeAccount.totalCapital > 0 ? Math.min((activeAccount.usedCapital / activeAccount.totalCapital) * 100, 100) : 0}%`,
                  background: (activeAccount.usedCapital / activeAccount.totalCapital) >= 0.5 ? '#FF6B6B' : '#00D4AA',
                }}
              />
            </div>
          </div>

          {/* 持仓列表 */}
          <div style={styles.positionsSection}>
            <div style={styles.positionsTitle}>持仓明细 ({activeAccount.positions.length})</div>
            {activeAccount.positions.length === 0 ? (
              <div style={styles.emptyPositions}>当前账户暂无持仓</div>
            ) : (
              <div style={styles.tableContainer}>
                <table style={styles.table}>
                  <thead>
                    <tr>
                      <th style={styles.th}>股票</th>
                      <th style={styles.th}>成本价</th>
                      <th style={styles.th}>现价</th>
                      <th style={styles.th}>数量</th>
                      <th style={styles.th}>市值</th>
                      <th style={styles.th}>盈亏</th>
                    </tr>
                  </thead>
                  <tbody>
                    {activeAccount.positions.map((p, idx) => (
                      <tr key={`${p.code}-${idx}`} style={styles.tr}>
                        <td style={styles.td}>
                          <div style={{ fontWeight: 600 }}>{p.name}</div>
                          <div style={{ fontSize: '12px', color: '#7A8BA7' }}>{p.code}</div>
                        </td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>¥{p.buyPrice.toFixed(2)}</td>
                        <td style={{ ...styles.td, fontFamily: 'monospace', fontWeight: 600 }}>¥{p.currentPrice.toFixed(2)}</td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>{p.volume}</td>
                        <td style={{ ...styles.td, fontFamily: 'monospace' }}>¥{p.marketValue.toLocaleString('zh-CN')}</td>
                        <td style={styles.td}>
                          <span style={{ color: p.profitPct >= 0 ? '#00D4AA' : '#FF6B6B', fontWeight: 600 }}>
                            {p.profitPct >= 0 ? '+' : ''}{p.profitPct.toFixed(2)}%
                          </span>
                        </td>
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )}
          </div>
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
    height: '100%',
    overflow: 'auto',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '4px',
    flexWrap: 'wrap',
    gap: '8px',
  },
  title: {
    fontSize: '15px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  addBtn: {
    padding: '6px 14px',
    border: 'none',
    borderRadius: '6px',
    background: '#00D4AA',
    color: '#0B1120',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
  },
  saveSuccess: {
    padding: '8px 12px',
    background: 'rgba(0,212,170,0.15)',
    border: '1px solid rgba(0,212,170,0.3)',
    borderRadius: '6px',
    color: '#00D4AA',
    fontSize: '13px',
  },
  formCard: {
    padding: '14px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  formTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
    marginBottom: '12px',
  },
  formRow: {
    display: 'flex',
    gap: '12px',
    alignItems: 'flex-end',
    flexWrap: 'wrap',
  },
  formItem: {
    display: 'flex',
    flexDirection: 'column',
    gap: '4px',
    flex: 1,
    minWidth: '140px',
  },
  formLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
  },
  formInput: {
    padding: '6px 10px',
    background: '#0B1120',
    border: '1px solid #243050',
    borderRadius: '4px',
    color: '#E8ECF4',
    fontSize: '13px',
    outline: 'none',
    fontFamily: 'inherit',
  },
  confirmBtn: {
    padding: '6px 16px',
    border: 'none',
    borderRadius: '6px',
    background: '#00D4AA',
    color: '#0B1120',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    height: '36px',
  },
  accountTabs: {
    display: 'flex',
    gap: '8px',
    flexWrap: 'wrap',
  },
  accountTab: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    gap: '2px',
    padding: '8px 16px',
    borderRadius: '8px',
    border: 'none',
    cursor: 'pointer',
    transition: 'all 0.2s',
    position: 'relative',
    minWidth: '100px',
  },
  tabName: {
    fontSize: '13px',
    fontWeight: 600,
  },
  tabCapital: {
    fontSize: '11px',
    opacity: 0.8,
  },
  tabClose: {
    position: 'absolute',
    top: '2px',
    right: '6px',
    fontSize: '14px',
    color: 'inherit',
    opacity: 0.5,
    cursor: 'pointer',
  },
  empty: {
    display: 'flex',
    flexDirection: 'column',
    alignItems: 'center',
    justifyContent: 'center',
    color: '#7A8BA7',
    padding: '40px',
  },
  emptyText: {
    fontSize: '15px',
    marginBottom: '4px',
  },
  emptySub: {
    fontSize: '12px',
    opacity: 0.6,
  },
  detailSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '12px',
  },
  overviewGrid: {
    display: 'grid',
    gridTemplateColumns: 'repeat(auto-fill, minmax(130px, 1fr))',
    gap: '10px',
  },
  overviewCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
    textAlign: 'center',
  },
  overviewLabel: {
    fontSize: '11px',
    color: '#7A8BA7',
    marginBottom: '6px',
  },
  overviewValue: {
    fontSize: '16px',
    fontWeight: 700,
    color: '#E8ECF4',
    fontFamily: 'monospace',
  },
  capitalBarCard: {
    padding: '12px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
  },
  capitalBarRow: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '8px',
  },
  capitalBarLabel: {
    fontSize: '12px',
    color: '#7A8BA7',
  },
  capitalBarText: {
    fontSize: '12px',
    color: '#E8ECF4',
    fontFamily: 'monospace',
  },
  capitalBarBg: {
    height: '8px',
    background: '#243050',
    borderRadius: '4px',
    overflow: 'hidden',
  },
  capitalBarFill: {
    height: '100%',
    borderRadius: '4px',
    transition: 'width 0.3s',
  },
  positionsSection: {
    display: 'flex',
    flexDirection: 'column',
    gap: '8px',
  },
  positionsTitle: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
    marginTop: '4px',
  },
  emptyPositions: {
    padding: '24px',
    textAlign: 'center',
    color: '#5A6B87',
    fontSize: '13px',
    background: '#1A2540',
    borderRadius: '8px',
    border: '1px solid #243050',
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
}

export default AccountManager
