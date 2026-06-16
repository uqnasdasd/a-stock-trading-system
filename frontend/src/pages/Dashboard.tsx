import React, { useState, useEffect, useRef, useCallback } from 'react'
import MarketIndices from '../components/MarketIndices'
import AuctionPanel from '../components/AuctionPanel'
import PositionPanel from '../components/PositionPanel'
import RiskPanel from '../components/RiskPanel'
import SignalPanel from '../components/SignalPanel'
import StockSearch from '../components/StockSearch'
import LimitMonitor from '../components/LimitMonitor'
import WatchlistPanel from '../components/WatchlistPanel'
import TradeLog from '../components/TradeLog'
import DailyReport from '../components/DailyReport'
import BacktestPanel from '../components/BacktestPanel'
import HistoryReplay from '../components/HistoryReplay'
import AccountManager from '../components/AccountManager'
import ConceptPanel from '../components/ConceptPanel'
import DragonTiger from '../components/DragonTiger'
import MultiStockCompare from '../components/MultiStockCompare'
import KlineChart from '../components/KlineChart'
import MinuteChart from '../components/MinuteChart'
import { useMarketData } from '../hooks/useMarketData'
import styles from './Dashboard.module.css'

/* ====== 导航项定义 ====== */
type NavKey =
  | 'overview'
  | 'auction'
  | 'position'
  | 'signal'
  | 'limit'
  | 'watchlist'
  | 'kline'
  | 'tradelog'
  | 'risk'
  | 'backtest'
  | 'replay'
  | 'concept'
  | 'dragon'
  | 'settings'

interface NavItem {
  key: NavKey
  icon: string
  label: string
}

const NAV_ITEMS: NavItem[] = [
  { key: 'overview', icon: '\u{1F4CA}', label: '大盘总览' },
  { key: 'auction', icon: '\u{1F525}', label: '竞价引擎' },
  { key: 'position', icon: '\u{1F4CB}', label: '持仓监控' },
  { key: 'signal', icon: '\u{1F6A8}', label: '信号预警' },
  { key: 'limit', icon: '\u{1F4C8}', label: '涨跌停' },
  { key: 'watchlist', icon: '\u2B50', label: '自选股' },
  { key: 'kline', icon: '\u{1F4CA}', label: 'K线/分时' },
  { key: 'tradelog', icon: '\u{1F4DD}', label: '交易日志' },
  { key: 'risk', icon: '\u{1F6E1}\uFE0F', label: '风控中心' },
  { key: 'backtest', icon: '\u{1F4C9}', label: '策略回测' },
  { key: 'replay', icon: '\u23F8', label: '历史回放' },
  { key: 'concept', icon: '\u{1F525}', label: '概念板块' },
  { key: 'dragon', icon: '\u{1F409}', label: '龙虎榜' },
  { key: 'settings', icon: '\u2699\uFE0F', label: '系统设置' },
]

/* ====== 键盘快捷键映射（Ctrl+数字） ====== */
const KEY_MAP: Record<string, NavKey> = {
  '1': 'overview',
  '2': 'auction',
  '3': 'position',
  '4': 'signal',
  '5': 'limit',
  '6': 'watchlist',
  '7': 'kline',
  '8': 'tradelog',
  '9': 'risk',
  '0': 'settings',
}

/* ====== Dashboard 主组件 ====== */
const Dashboard: React.FC = () => {
  const [activeNav, setActiveNav] = useState<NavKey>('overview')
  const { data, isConnected, isLoading, refresh } = useMarketData()
  const [showShortcuts, setShowShortcuts] = useState(false)

  // 尾盘提醒：14:45-15:00
  const [showClosingAlert, setShowClosingAlert] = useState(false)
  const [closingMinutes, setClosingMinutes] = useState(0)

  // 顶部搜索框状态
  const [searchQuery, setSearchQuery] = useState('')
  const [searchResults, setSearchResults] = useState<any[]>([])
  const [showSearchDropdown, setShowSearchDropdown] = useState(false)
  const searchRef = useRef<HTMLDivElement>(null)
  const searchInputRef = useRef<HTMLInputElement>(null)

  // 添加持仓模态框状态
  const [showAddPositionModal, setShowAddPositionModal] = useState(false)
  const [positionModalStock, setPositionModalStock] = useState<any>(null)
  const [positionVolume, setPositionVolume] = useState('100')
  const [positionStopLoss, setPositionStopLoss] = useState('')
  const [positionTakeProfit, setPositionTakeProfit] = useState('')
  const [positionSubmitting, setPositionSubmitting] = useState(false)

  // K线/分时页面状态
  const [klineCode, setKlineCode] = useState('')
  const [klineName, setKlineName] = useState('')
  const [klineSearchQuery, setKlineSearchQuery] = useState('')
  const [klineSearchResults, setKlineSearchResults] = useState<any[]>([])
  const [showKlineSearch, setShowKlineSearch] = useState(false)
  const [showMinuteChart, setShowMinuteChart] = useState(false)

  useEffect(() => {
    const checkClosingTime = () => {
      const now = new Date()
      const hours = now.getHours()
      const minutes = now.getMinutes()
      const currentMinutes = hours * 60 + minutes

      if (currentMinutes >= 885 && currentMinutes < 900) {
        setShowClosingAlert(true)
        setClosingMinutes(900 - currentMinutes)
      } else {
        setShowClosingAlert(false)
      }
    }

    checkClosingTime()
    const timer = setInterval(checkClosingTime, 10000)
    return () => clearInterval(timer)
  }, [])

  // 点击外部关闭搜索下拉
  useEffect(() => {
    const handleClickOutside = (e: MouseEvent) => {
      if (searchRef.current && !searchRef.current.contains(e.target as Node)) {
        setShowSearchDropdown(false)
      }
    }
    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return

      const num = e.key
      if (KEY_MAP[num]) {
        e.preventDefault()
        setActiveNav(KEY_MAP[num])
        return
      }

      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault()
        searchInputRef.current?.focus()
        return
      }

      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault()
        if (refresh) refresh()
        return
      }

      if (e.key === '/') {
        e.preventDefault()
        setShowShortcuts(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [refresh])

  // 顶部搜索功能
  const handleSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setSearchResults([])
      setShowSearchDropdown(false)
      return
    }

    try {
      const res = await fetch(`/api/stock/search?code=${encodeURIComponent(query)}`)
      const result = await res.json()
      if (result.found) {
        setSearchResults([result])
      } else {
        setSearchResults([])
      }
      setShowSearchDropdown(true)
    } catch {
      setSearchResults([])
    }
  }, [])

  const handleSearchKeyDown = (e: React.KeyboardEvent) => {
    if (e.key === 'Enter') {
      handleSearch(searchQuery)
    }
  }

  const handleSearchChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    setSearchQuery(e.target.value)
    if (e.target.value.trim()) {
      handleSearch(e.target.value)
    } else {
      setShowSearchDropdown(false)
    }
  }

  // 添加持仓（模态框方式）
  const openAddPositionModal = (stock: any) => {
    setPositionModalStock(stock)
    setPositionVolume('100')
    setPositionStopLoss(stock ? (stock.price * 0.97).toFixed(2) : '')
    setPositionTakeProfit(stock ? (stock.price * 1.05).toFixed(2) : '')
    setShowAddPositionModal(true)
    setShowSearchDropdown(false)
  }

  const submitAddPosition = async () => {
    if (!positionModalStock || !positionVolume) return
    setPositionSubmitting(true)
    try {
      const res = await fetch('/api/positions', {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          code: positionModalStock.code,
          name: positionModalStock.name,
          buy_price: positionModalStock.price,
          current_price: positionModalStock.price,
          volume: parseInt(positionVolume),
          sector: '',
          buy_time: new Date().toISOString(),
          stop_loss_price: parseFloat(positionStopLoss) || +(positionModalStock.price * 0.97).toFixed(2),
          take_profit_price: parseFloat(positionTakeProfit) || +(positionModalStock.price * 1.05).toFixed(2),
        }),
      })
      await res.json()
      setShowAddPositionModal(false)
      if (refresh) refresh()
    } catch {
      // 静默失败
    } finally {
      setPositionSubmitting(false)
    }
  }

  // K线搜索
  const handleKlineSearch = useCallback(async (query: string) => {
    if (!query.trim()) {
      setKlineSearchResults([])
      setShowKlineSearch(false)
      return
    }
    try {
      const res = await fetch(`/api/stock/search?code=${encodeURIComponent(query)}`)
      const result = await res.json()
      if (result.found) {
        setKlineSearchResults([result])
        setShowKlineSearch(true)
      } else {
        setKlineSearchResults([])
      }
    } catch {
      setKlineSearchResults([])
    }
  }, [])

  // ====== 渲染顶部指数栏 ======
  const renderIndicesBar = () => {
    const indices = data?.indices
    if (!indices || indices.length === 0) {
      return (
        <div className={styles.indicesRow}>
          <span style={{ color: '#bbb', fontSize: 13 }}>暂无指数数据</span>
        </div>
      )
    }

    return (
      <div className={styles.indicesRow}>
        {indices.map((idx: any) => {
          const isUp = idx.change_pct > 0
          const colorClass = isUp ? styles.indexUp : idx.change_pct < 0 ? styles.indexDown : styles.indexFlat
          return (
            <div key={idx.code} className={styles.indexCard}>
              <span className={styles.indexName}>{idx.name}</span>
              <span className={`${styles.indexPrice} ${colorClass}`}>
                {idx.price?.toFixed(2) ?? '--'}
              </span>
              <span className={`${styles.indexChange} ${colorClass}`}>
                {isUp ? '+' : ''}{idx.change_pct?.toFixed(2) ?? '--'}%
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  // ====== 渲染大盘总览页面 ======
  const renderOverview = () => {
    const positions = data?.positions
    const risk = data?.risk
    const auction = data?.auction
    const limit = data?.limit
    const indices = data?.indices

    // 计算市场情绪（从indices或limit数据获取）
    const upCount = indices?.reduce((sum: number, idx: any) => sum + (idx.change_pct > 0 ? 1 : 0), 0) ?? limit?.limit_up_count ?? 0
    const downCount = indices?.reduce((sum: number, idx: any) => sum + (idx.change_pct < 0 ? 1 : 0), 0) ?? limit?.limit_down_count ?? 0
    const limitUp = limit?.limit_up_count ?? 0
    const limitDown = limit?.limit_down_count ?? 0
    const total = upCount + downCount || 1
    const sentimentScore = Math.round(((upCount - downCount) / total) * 100 + 50)
    const clampedScore = Math.max(0, Math.min(100, sentimentScore))

    // 板块强度TOP5（从auction数据中提取）
    const sectors = auction?.sector_strengths?.slice(0, 5) ?? []

    // 龙头竞价评分（从auction数据中提取）
    const dragons = auction?.leader_scores?.slice(0, 5) ?? []

    return (
      <div className={styles.overviewGrid}>
        {/* 市场情绪卡片 */}
        <div className={`${styles.card} ${styles.overviewSentiment}`}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>市场情绪</h3>
            <span style={{ fontSize: 12, color: '#999' }}>
              {data?.timestamp ? new Date(data.timestamp).toLocaleTimeString('zh-CN') : '--'}
            </span>
          </div>
          <div className={styles.cardBody}>
            <div className={styles.sentimentRow}>
              <div className={styles.sentimentItem}>
                <div className={styles.sentimentLabel}>情绪评分</div>
                <div className={`${styles.sentimentScore} ${
                  clampedScore > 60 ? styles.sentimentScoreBullish :
                  clampedScore < 40 ? styles.sentimentScoreBearish :
                  styles.sentimentScoreNeutral
                }`}>
                  {clampedScore}
                </div>
              </div>
              <div className={styles.sentimentItem}>
                <div className={styles.sentimentLabel}>涨/跌家数</div>
                <div className={styles.sentimentValue}>
                  <span className={styles.sentimentUpCount}>{upCount}</span>
                  <span style={{ color: '#999', margin: '0 4px' }}>/</span>
                  <span className={styles.sentimentDownCount}>{downCount}</span>
                </div>
              </div>
              <div className={styles.sentimentItem}>
                <div className={styles.sentimentLabel}>涨停 / 跌停</div>
                <div className={styles.sentimentValue}>
                  <span className={styles.sentimentUpCount}>{limitUp}</span>
                  <span style={{ color: '#999', margin: '0 4px' }}>/</span>
                  <span className={styles.sentimentDownCount}>{limitDown}</span>
                </div>
              </div>
            </div>
          </div>
        </div>

        {/* 板块强度TOP5 */}
        <div className={`${styles.card} ${styles.overviewSector}`}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>板块强度 TOP5</h3>
          </div>
          <div className={styles.cardBody}>
            {sectors.length > 0 ? (
              <div className={styles.sectorList}>
                {sectors.map((s: any, i: number) => (
                  <div key={i} className={styles.sectorItem}>
                    <span className={styles.sectorRank}>{i + 1}</span>
                    <span className={styles.sectorName}>{s.name ?? '--'}</span>
                    <span className={`${styles.sectorChange} ${s.change_pct > 0 ? styles.indexUp : styles.indexDown}`}>
                      {s.change_pct > 0 ? '+' : ''}{s.change_pct?.toFixed(2)}%
                    </span>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>暂无板块数据</div>
            )}
          </div>
        </div>

        {/* 龙头竞价评分 */}
        <div className={`${styles.card} ${styles.overviewAuction}`}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>龙头竞价评分</h3>
          </div>
          <div className={styles.cardBody}>
            {dragons.length > 0 ? (
              <div className={styles.auctionList}>
                {dragons.map((d: any, i: number) => (
                  <div key={i} className={styles.auctionItem}>
                    <div>
                      <span className={styles.auctionName}>{d.name ?? '--'}</span>
                      <span className={styles.auctionCode}>{d.code ?? ''}</span>
                    </div>
                    <div style={{ textAlign: 'right' }}>
                      <span className={styles.auctionScore}>{d.score ?? '--'}</span>
                      <span className={styles.auctionScoreLabel}>分</span>
                    </div>
                  </div>
                ))}
              </div>
            ) : (
              <div className={styles.emptyState}>暂无竞价数据</div>
            )}
          </div>
        </div>

        {/* 持仓列表 */}
        <div className={`${styles.card} ${styles.overviewPosition}`}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>持仓列表</h3>
          </div>
          <div className={styles.cardBody}>
            <PositionPanel data={positions} />
          </div>
        </div>

        {/* 风控状态 */}
        <div className={`${styles.card} ${styles.overviewRisk}`}>
          <div className={styles.cardHeader}>
            <h3 className={styles.cardTitle}>风控状态</h3>
          </div>
          <div className={styles.cardBody}>
            <RiskPanel data={risk} />
          </div>
        </div>
      </div>
    )
  }

  // ====== 渲染K线/分时页面 ======
  const renderKlinePage = () => (
    <div className={styles.panelContainer}>
      <div style={{ marginBottom: 12 }}>
        <div style={{ display: 'flex', gap: 8, marginBottom: 8 }}>
          <input
            style={{
              flex: 1, padding: '8px 12px', background: '#fff',
              border: '1px solid #e0e0e0', borderRadius: 6,
              color: '#333', fontSize: 14, outline: 'none', fontFamily: 'inherit',
            }}
            placeholder="输入股票代码查看K线/分时 (如: 600519)"
            value={klineSearchQuery}
            onChange={(e) => {
              setKlineSearchQuery(e.target.value)
              handleKlineSearch(e.target.value)
            }}
            onKeyDown={(e) => {
              if (e.key === 'Enter') handleKlineSearch(klineSearchQuery)
            }}
          />
          <button
            style={{
              padding: '8px 16px', background: '#e94560', color: '#fff',
              border: 'none', borderRadius: 6, fontSize: 14, fontWeight: 600,
              cursor: 'pointer', fontFamily: 'inherit',
            }}
            onClick={() => handleKlineSearch(klineSearchQuery)}
          >
            搜索
          </button>
          {klineCode && (
            <button
              style={{
                padding: '8px 16px', background: '#f5f5f5', color: '#666',
                border: '1px solid #e0e0e0', borderRadius: 6, fontSize: 14,
                cursor: 'pointer', fontFamily: 'inherit',
              }}
              onClick={() => setShowMinuteChart(!showMinuteChart)}
            >
              {showMinuteChart ? '切换K线' : '切换分时'}
            </button>
          )}
        </div>
        {showKlineSearch && klineSearchResults.length > 0 && (
          <div style={{
            background: '#fff', border: '1px solid #e0e0e0', borderRadius: 6,
            padding: '8px 12px', marginBottom: 8, cursor: 'pointer',
          }}
          onClick={() => {
            const s = klineSearchResults[0]
            setKlineCode(s.code)
            setKlineName(s.name)
            setShowKlineSearch(false)
            setKlineSearchQuery(`${s.name}(${s.code})`)
          }}
          >
            {klineSearchResults[0].name} ({klineSearchResults[0].code}) - 点击查看图表
          </div>
        )}
      </div>
      {klineCode && klineName && (
        showMinuteChart
          ? <MinuteChart code={klineCode} name={klineName} />
          : <KlineChart code={klineCode} name={klineName} />
      )}
      {!klineCode && (
        <div className={styles.emptyState}>请输入股票代码查看K线或分时图</div>
      )}
    </div>
  )

  // ====== 渲染主内容区 ======
  const renderContent = () => {
    switch (activeNav) {
      case 'overview':
        return renderOverview()
      case 'auction':
        return <div className={styles.panelContainer}><AuctionPanel data={data?.auction} /></div>
      case 'position':
        return <div className={styles.panelContainer}><PositionPanel data={data?.positions} /></div>
      case 'signal':
        return <div className={styles.panelContainer}><SignalPanel data={data?.signals} /></div>
      case 'limit':
        return <div className={styles.panelContainer}><LimitMonitor /></div>
      case 'watchlist':
        return <div className={styles.panelContainer}><WatchlistPanel /></div>
      case 'kline':
        return renderKlinePage()
      case 'tradelog':
        return <div className={styles.panelContainer}><TradeLog /></div>
      case 'risk':
        return <div className={styles.panelContainer}><RiskPanel data={data?.risk} /></div>
      case 'backtest':
        return <div className={styles.panelContainer}><BacktestPanel /></div>
      case 'replay':
        return <div className={styles.panelContainer}><HistoryReplay /></div>
      case 'concept':
        return <div className={styles.panelContainer}><ConceptPanel /></div>
      case 'dragon':
        return <div className={styles.panelContainer}><DragonTiger /></div>
      case 'settings':
        return (
          <div className={styles.panelContainer}>
            <div className={styles.card}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>系统设置</h3>
              </div>
              <div className={styles.cardBody}>
                <AccountManager />
              </div>
            </div>
            <div className={styles.card} style={{ marginTop: 16 }}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>复盘报告</h3>
              </div>
              <div className={styles.cardBody}>
                <DailyReport />
              </div>
            </div>
            <div className={styles.card} style={{ marginTop: 16 }}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>回测面板</h3>
              </div>
              <div className={styles.cardBody}>
                <BacktestPanel />
              </div>
            </div>
            <div className={styles.card} style={{ marginTop: 16 }}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>多股对比</h3>
              </div>
              <div className={styles.cardBody}>
                <MultiStockCompare />
              </div>
            </div>
            <div className={styles.card} style={{ marginTop: 16 }}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>股票搜索</h3>
              </div>
              <div className={styles.cardBody}>
                <StockSearch />
              </div>
            </div>
            <div className={styles.card} style={{ marginTop: 16 }}>
              <div className={styles.cardHeader}>
                <h3 className={styles.cardTitle}>大盘指数</h3>
              </div>
              <div className={styles.cardBody}>
                <MarketIndices data={data?.indices} isLoading={isLoading} />
              </div>
            </div>
          </div>
        )
      default:
        return <div className={styles.emptyState}>页面不存在</div>
    }
  }

  return (
    <div className={styles.container}>
      {/* ====== 左侧导航栏 ====== */}
      <nav className={styles.sidebar}>
        <div className={styles.sidebarHeader}>
          <h1 className={styles.sidebarTitle}>A股超短交易</h1>
          <div className={styles.sidebarSubtitle}>实时监测系统</div>
        </div>

        <div className={styles.navList}>
          {NAV_ITEMS.map((item) => (
            <button
              key={item.key}
              className={`${styles.navItem} ${activeNav === item.key ? styles.navItemActive : ''}`}
              onClick={() => setActiveNav(item.key)}
            >
              <span className={styles.navIcon}>{item.icon}</span>
              <span className={styles.navLabel}>{item.label}</span>
            </button>
          ))}
        </div>

        <div className={styles.sidebarFooter}>
          <span className={`${styles.statusDot} ${isConnected ? styles.statusDotConnected : styles.statusDotDisconnected}`} />
          <span className={styles.sidebarStatusText}>
            {isConnected ? 'WebSocket 已连接' : 'WebSocket 未连接'}
          </span>
        </div>
      </nav>

      {/* ====== 右侧主内容区 ====== */}
      <div className={styles.mainArea}>
        {/* 顶部状态栏 */}
        <div className={styles.topBar}>
          {renderIndicesBar()}

          <div className={styles.topBarRight}>
            {isLoading && <span className={styles.topBarLoading}>加载中...</span>}
            {data?.timestamp && (
              <span className={styles.topBarTime}>
                更新: {new Date(data.timestamp).toLocaleTimeString('zh-CN')}
              </span>
            )}

            {/* 搜索框 */}
            <div className={styles.searchBox} ref={searchRef}>
              <span className={styles.searchIcon}>&#128269;</span>
              <input
                ref={searchInputRef}
                className={styles.searchInput}
                placeholder="搜索股票代码..."
                value={searchQuery}
                onChange={handleSearchChange}
                onKeyDown={handleSearchKeyDown}
              />
              {showSearchDropdown && searchResults.length > 0 && (
                <div className={styles.searchDropdown}>
                  {searchResults.map((s: any) => (
                    <div key={s.code} className={styles.searchDropdownItem} onClick={() => openAddPositionModal(s)}>
                      <div>
                        <span className={styles.searchDropdownName}>{s.name}</span>
                        <span className={styles.searchDropdownCode}>{s.code}</span>
                      </div>
                      <span className={`${styles.searchDropdownPrice} ${s.change_pct >= 0 ? styles.indexUp : styles.indexDown}`}>
                        {s.price?.toFixed(2)}
                      </span>
                    </div>
                  ))}
                </div>
              )}
            </div>

            <button
              className={styles.shortcutBtn}
              onClick={() => setShowShortcuts(!showShortcuts)}
              title="快捷键提示 (Ctrl+/)"
            >
              &#9000;
            </button>
          </div>
        </div>

        {/* 尾盘操作提醒条 */}
        {showClosingAlert && (
          <div className={styles.closingAlert}>
            <div className={styles.closingAlertContent}>
              <span className={styles.closingAlertIcon}>&#9888;</span>
              <span className={styles.closingAlertText}>
                尾盘提醒 - 距收盘还有 {closingMinutes} 分钟
              </span>
              <span className={styles.closingAlertActions}>
                请检查持仓，执行隔夜风控：非涨停股需清仓，确认止损位已设置
              </span>
            </div>
          </div>
        )}

        {/* 中间内容区 */}
        <div className={styles.contentArea}>
          {renderContent()}
        </div>

        {/* 底部状态栏 */}
        <div className={styles.bottomBar}>
          <div className={styles.bottomBarLeft}>
            <span className={`${styles.statusDot} ${isConnected ? styles.statusDotConnected : styles.statusDotDisconnected}`} />
            <span style={{ fontSize: 12, color: '#999' }}>
              {isConnected ? '数据连接正常' : '数据连接断开，正在重连...'}
            </span>
          </div>
          <div className={styles.bottomBarRight}>
            {data?.timestamp
              ? `数据刷新: ${new Date(data.timestamp).toLocaleTimeString('zh-CN')}`
              : '等待数据...'}
          </div>
        </div>
      </div>

      {/* ====== 快捷键提示弹窗 ====== */}
      {showShortcuts && (
        <div className={styles.shortcutOverlay} onClick={() => setShowShortcuts(false)}>
          <div className={styles.shortcutModal} onClick={e => e.stopPropagation()}>
            <div className={styles.shortcutHeader}>
              <h3 className={styles.shortcutTitle}>键盘快捷键</h3>
              <button className={styles.shortcutClose} onClick={() => setShowShortcuts(false)}>&times;</button>
            </div>
            <div className={styles.shortcutList}>
              <div className={styles.shortcutItem}>
                <span className={styles.shortcutKey}>Ctrl + 1~0</span>
                <span className={styles.shortcutDesc}>切换导航页面</span>
              </div>
              <div className={styles.shortcutItem}>
                <span className={styles.shortcutKey}>Ctrl + F</span>
                <span className={styles.shortcutDesc}>聚焦搜索框</span>
              </div>
              <div className={styles.shortcutItem}>
                <span className={styles.shortcutKey}>Ctrl + R</span>
                <span className={styles.shortcutDesc}>刷新数据</span>
              </div>
              <div className={styles.shortcutItem}>
                <span className={styles.shortcutKey}>Ctrl + /</span>
                <span className={styles.shortcutDesc}>显示/隐藏快捷键提示</span>
              </div>
            </div>
          </div>
        </div>
      )}

      {/* ====== 添加持仓模态框 ====== */}
      {showAddPositionModal && positionModalStock && (
        <div className={styles.modalOverlay} onClick={() => setShowAddPositionModal(false)}>
          <div className={styles.modal} onClick={e => e.stopPropagation()}>
            <div className={styles.modalHeader}>
              <h3 className={styles.modalTitle}>添加持仓</h3>
              <button className={styles.modalClose} onClick={() => setShowAddPositionModal(false)}>&times;</button>
            </div>
            <div className={styles.modalBody}>
              <div className={styles.modalStockInfo}>
                <div>
                  <div className={styles.modalStockName}>{positionModalStock.name}</div>
                  <div className={styles.modalStockCode}>{positionModalStock.code}</div>
                </div>
                <span className={`${styles.modalStockPrice} ${positionModalStock.change_pct >= 0 ? styles.indexUp : styles.indexDown}`}>
                  {positionModalStock.price?.toFixed(2)}
                </span>
              </div>
              <div className={styles.modalField}>
                <label className={styles.modalLabel}>买入数量（股）</label>
                <input
                  className={styles.modalInput}
                  type="number"
                  value={positionVolume}
                  onChange={e => setPositionVolume(e.target.value)}
                  placeholder="请输入买入股数"
                />
              </div>
              <div className={styles.modalField}>
                <label className={styles.modalLabel}>止损价（元）</label>
                <input
                  className={styles.modalInput}
                  type="number"
                  step="0.01"
                  value={positionStopLoss}
                  onChange={e => setPositionStopLoss(e.target.value)}
                  placeholder="默认买入价 -3%"
                />
              </div>
              <div className={styles.modalField}>
                <label className={styles.modalLabel}>止盈价（元）</label>
                <input
                  className={styles.modalInput}
                  type="number"
                  step="0.01"
                  value={positionTakeProfit}
                  onChange={e => setPositionTakeProfit(e.target.value)}
                  placeholder="默认买入价 +5%"
                />
              </div>
            </div>
            <div className={styles.modalFooter}>
              <button className={styles.modalBtnCancel} onClick={() => setShowAddPositionModal(false)}>
                取消
              </button>
              <button
                className={styles.modalBtnConfirm}
                onClick={submitAddPosition}
                disabled={positionSubmitting || !positionVolume}
              >
                {positionSubmitting ? '提交中...' : '确认买入'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

export default Dashboard
