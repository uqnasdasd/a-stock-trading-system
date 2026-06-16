import React, { useState, useEffect } from 'react'
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
import AccountManager from '../components/AccountManager'
import ConceptPanel from '../components/ConceptPanel'
import DragonTiger from '../components/DragonTiger'
import MultiStockCompare from '../components/MultiStockCompare'
import { useMarketData } from '../hooks/useMarketData'

type TabKey = 'auction' | 'position' | 'signal' | 'limit' | 'watchlist' | 'tradelog' | 'report' | 'backtest' | 'account' | 'concept' | 'dragon' | 'compare'

const TAB_ORDER: TabKey[] = ['auction', 'position', 'signal', 'limit', 'watchlist', 'concept', 'dragon', 'compare', 'tradelog', 'report', 'backtest', 'account']

const TAB_LABELS: Record<TabKey, string> = {
  auction: '竞价引擎',
  position: '持仓监控',
  signal: '信号列表',
  limit: '涨跌停',
  watchlist: '自选股',
  tradelog: '交易日志',
  report: '复盘',
  backtest: '回测',
  account: '账户',
  concept: '概念',
  dragon: '龙虎榜',
  compare: '对比',
}

const Dashboard: React.FC = () => {
  const [activeTab, setActiveTab] = useState<TabKey>('auction')
  const { data, isConnected, isLoading, refresh } = useMarketData()
  const [showShortcuts, setShowShortcuts] = useState(false)

  // 尾盘提醒：14:45-15:00
  const [showClosingAlert, setShowClosingAlert] = useState(false)
  const [closingMinutes, setClosingMinutes] = useState(0)

  useEffect(() => {
    const checkClosingTime = () => {
      const now = new Date()
      const hours = now.getHours()
      const minutes = now.getMinutes()
      const currentMinutes = hours * 60 + minutes

      // 14:45 = 885, 15:00 = 900
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

  // 键盘快捷键
  useEffect(() => {
    const handleKeyDown = (e: KeyboardEvent) => {
      if (!e.ctrlKey) return

      // Ctrl+1~9 切换标签页
      const num = parseInt(e.key)
      if (!isNaN(num) && num >= 1 && num <= TAB_ORDER.length) {
        e.preventDefault()
        setActiveTab(TAB_ORDER[num - 1])
        return
      }

      // Ctrl+F 聚焦搜索框
      if (e.key === 'f' || e.key === 'F') {
        e.preventDefault()
        // 尝试聚焦 StockSearch 中的 input
        const inputs = document.querySelectorAll<HTMLInputElement>('input[placeholder*="股票"]')
        if (inputs.length > 0) {
          inputs[0].focus()
        }
        return
      }

      // Ctrl+R 刷新数据
      if (e.key === 'r' || e.key === 'R') {
        e.preventDefault()
        if (refresh) refresh()
        window.location.reload()
        return
      }

      // Ctrl+/ 显示快捷键提示
      if (e.key === '/') {
        e.preventDefault()
        setShowShortcuts(prev => !prev)
      }
    }

    window.addEventListener('keydown', handleKeyDown)
    return () => window.removeEventListener('keydown', handleKeyDown)
  }, [refresh])

  const statusDotStyle: React.CSSProperties = {
    width: '8px',
    height: '8px',
    borderRadius: '50%',
    background: isConnected ? '#00D4AA' : '#FF6B6B',
    boxShadow: isConnected ? '0 0 8px #00D4AA' : '0 0 8px #FF6B6B',
  }

  return (
    <div style={styles.container}>
      {/* 顶部栏 */}
      <header style={styles.header}>
        <div style={styles.title}>
          <span style={styles.logo}>📈</span>
          <h1 style={styles.heading}>A股超短交易实时监测系统</h1>
        </div>
        <div style={styles.status}>
          {isLoading && <span style={styles.loading}>加载中...</span>}
          <span style={statusDotStyle} />
          <span style={styles.statusText}>{isConnected ? '已连接' : '未连接'}</span>
          {data?.timestamp && (
            <span style={styles.time}>
              更新: {new Date(data.timestamp).toLocaleTimeString('zh-CN')}
            </span>
          )}
          <button
            style={styles.shortcutBtn}
            onClick={() => setShowShortcuts(!showShortcuts)}
            title="快捷键提示 (Ctrl+/)"
          >
            ⌨
          </button>
        </div>
      </header>

      {/* 尾盘操作提醒条 */}
      {showClosingAlert && (
        <div style={styles.closingAlert}>
          <div style={styles.closingAlertContent}>
            <span style={styles.closingAlertIcon}>⚠</span>
            <span style={styles.closingAlertText}>
              尾盘提醒 - 距收盘还有 {closingMinutes} 分钟
            </span>
            <span style={styles.closingAlertActions}>
              请检查持仓，执行隔夜风控：非涨停股需清仓，确认止损位已设置
            </span>
          </div>
        </div>
      )}

      {/* 大盘指数栏 */}
      <MarketIndices data={data?.indices} isLoading={isLoading} />

      {/* 主内容区 */}
      <div style={styles.main}>
        {/* 左侧：切换面板 */}
        <div style={styles.leftPanel}>
          <StockSearch />
          <div style={styles.tabs}>
            {TAB_ORDER.map((key) => (
              <TabButton
                key={key}
                active={activeTab === key}
                onClick={() => setActiveTab(key)}
                label={TAB_LABELS[key]}
              />
            ))}
          </div>

          <div style={styles.tabContent}>
            {activeTab === 'auction' && <AuctionPanel data={data?.auction} />}
            {activeTab === 'position' && <PositionPanel data={data?.positions} />}
            {activeTab === 'signal' && <SignalPanel data={data?.signals} />}
            {activeTab === 'limit' && <LimitMonitor />}
            {activeTab === 'watchlist' && <WatchlistPanel />}
            {activeTab === 'tradelog' && <TradeLog />}
            {activeTab === 'report' && <DailyReport />}
            {activeTab === 'backtest' && <BacktestPanel />}
            {activeTab === 'account' && <AccountManager />}
            {activeTab === 'concept' && <ConceptPanel />}
            {activeTab === 'dragon' && <DragonTiger />}
            {activeTab === 'compare' && <MultiStockCompare />}
          </div>
        </div>

        {/* 右侧：风控面板 */}
        <div style={styles.rightPanel}>
          <RiskPanel data={data?.risk} />
        </div>
      </div>

      {/* 快捷键提示弹窗 */}
      {showShortcuts && (
        <div style={styles.shortcutOverlay} onClick={() => setShowShortcuts(false)}>
          <div style={styles.shortcutModal} onClick={e => e.stopPropagation()}>
            <div style={styles.shortcutHeader}>
              <h3 style={styles.shortcutTitle}>键盘快捷键</h3>
              <button style={styles.shortcutClose} onClick={() => setShowShortcuts(false)}>×</button>
            </div>
            <div style={styles.shortcutList}>
              <div style={styles.shortcutItem}>
                <span style={styles.shortcutKey}>Ctrl + 1~9</span>
                <span style={styles.shortcutDesc}>切换标签页</span>
              </div>
              <div style={styles.shortcutItem}>
                <span style={styles.shortcutKey}>Ctrl + F</span>
                <span style={styles.shortcutDesc}>聚焦搜索框</span>
              </div>
              <div style={styles.shortcutItem}>
                <span style={styles.shortcutKey}>Ctrl + R</span>
                <span style={styles.shortcutDesc}>刷新数据</span>
              </div>
              <div style={styles.shortcutItem}>
                <span style={styles.shortcutKey}>Ctrl + /</span>
                <span style={styles.shortcutDesc}>显示/隐藏快捷键提示</span>
              </div>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

const TabButton: React.FC<{ active: boolean; onClick: () => void; label: string }> = ({ active, onClick, label }) => {
  const style: React.CSSProperties = {
    padding: '8px 16px',
    border: 'none',
    borderRadius: '6px',
    background: active ? '#00D4AA' : '#1A2540',
    color: active ? '#0B1120' : '#7A8BA7',
    fontSize: '13px',
    fontWeight: 600,
    cursor: 'pointer',
    transition: 'all 0.2s',
    whiteSpace: 'nowrap',
    flexShrink: 0,
  }
  return <button style={style} onClick={onClick}>{label}</button>
}

const styles: Record<string, React.CSSProperties> = {
  container: {
    display: 'flex',
    flexDirection: 'column',
    height: '100vh',
    background: '#0B1120',
    color: '#E8ECF4',
    fontFamily: '-apple-system, "PingFang SC", "Microsoft YaHei", sans-serif',
  },
  header: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '12px 24px',
    background: '#131B2E',
    borderBottom: '1px solid #243050',
    flexWrap: 'wrap',
    gap: '8px',
  },
  title: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  logo: {
    fontSize: '24px',
  },
  heading: {
    fontSize: '18px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  status: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
  },
  loading: {
    fontSize: '12px',
    color: '#FFB84D',
  },
  statusText: {
    fontSize: '13px',
    color: '#7A8BA7',
  },
  time: {
    fontSize: '11px',
    color: '#5A6B87',
    fontFamily: 'monospace',
  },
  shortcutBtn: {
    padding: '4px 8px',
    border: '1px solid #243050',
    borderRadius: '4px',
    background: '#1A2540',
    color: '#7A8BA7',
    fontSize: '14px',
    cursor: 'pointer',
    lineHeight: 1,
  },
  closingAlert: {
    padding: '10px 24px',
    background: 'linear-gradient(90deg, rgba(255,184,77,0.15) 0%, rgba(255,107,107,0.15) 100%)',
    borderBottom: '1px solid rgba(255,184,77,0.4)',
    animation: 'pulse 2s ease-in-out infinite',
  },
  closingAlertContent: {
    display: 'flex',
    alignItems: 'center',
    gap: '12px',
    maxWidth: '1200px',
    margin: '0 auto',
    flexWrap: 'wrap',
  },
  closingAlertIcon: {
    fontSize: '18px',
    color: '#FFB84D',
  },
  closingAlertText: {
    fontSize: '14px',
    fontWeight: 700,
    color: '#FFB84D',
    whiteSpace: 'nowrap',
  },
  closingAlertActions: {
    fontSize: '13px',
    color: '#E8ECF4',
  },
  main: {
    display: 'flex',
    flex: 1,
    overflow: 'hidden',
    padding: '16px',
    gap: '16px',
  },
  leftPanel: {
    flex: 1,
    display: 'flex',
    flexDirection: 'column',
    minWidth: 0,
  },
  tabs: {
    display: 'flex',
    gap: '4px',
    marginBottom: '12px',
    overflowX: 'auto',
    paddingBottom: '4px',
    scrollbarWidth: 'thin',
    scrollbarColor: '#243050 transparent',
  },
  tabContent: {
    flex: 1,
    overflow: 'auto',
    background: '#131B2E',
    borderRadius: '8px',
    border: '1px solid #243050',
    padding: '16px',
  },
  rightPanel: {
    width: '320px',
    flexShrink: 0,
  },
  shortcutOverlay: {
    position: 'fixed',
    top: 0,
    left: 0,
    right: 0,
    bottom: 0,
    background: 'rgba(0,0,0,0.6)',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    zIndex: 1000,
  },
  shortcutModal: {
    background: '#1A2540',
    borderRadius: '12px',
    border: '1px solid #243050',
    padding: '20px',
    minWidth: '320px',
    maxWidth: '90vw',
    boxShadow: '0 20px 60px rgba(0,0,0,0.5)',
  },
  shortcutHeader: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    marginBottom: '16px',
    paddingBottom: '12px',
    borderBottom: '1px solid #243050',
  },
  shortcutTitle: {
    fontSize: '16px',
    fontWeight: 600,
    color: '#E8ECF4',
    margin: 0,
  },
  shortcutClose: {
    padding: '2px 8px',
    border: 'none',
    borderRadius: '4px',
    background: 'transparent',
    color: '#7A8BA7',
    fontSize: '20px',
    cursor: 'pointer',
    lineHeight: 1,
  },
  shortcutList: {
    display: 'flex',
    flexDirection: 'column',
    gap: '10px',
  },
  shortcutItem: {
    display: 'flex',
    justifyContent: 'space-between',
    alignItems: 'center',
    padding: '8px 12px',
    background: '#0B1120',
    borderRadius: '6px',
  },
  shortcutKey: {
    fontSize: '13px',
    fontWeight: 600,
    color: '#00D4AA',
    fontFamily: 'monospace',
    background: '#1A2540',
    padding: '2px 8px',
    borderRadius: '4px',
    border: '1px solid #243050',
  },
  shortcutDesc: {
    fontSize: '13px',
    color: '#B8C4D4',
  },
}

// 移动端媒体查询样式注入
const mobileStyles = `
@media (max-width: 768px) {
  #root > div > header {
    padding: 8px 12px !important;
  }
  #root > div > header h1 {
    font-size: 14px !important;
  }
  #root > div > header .logo {
    font-size: 18px !important;
  }
  #root > div > div[style*="padding: 12px 24px"] {
    padding: 8px 12px !important;
  }
  #root > div > div[style*="display: flex; flex: 1"] {
    flex-direction: column !important;
    padding: 8px !important;
    gap: 8px !important;
    overflow: auto !important;
  }
  #root > div > div[style*="display: flex; flex: 1"] > div:last-child {
    width: 100% !important;
    order: 99 !important;
  }
  #root > div > div[style*="display: flex; flex: 1"] > div:first-child {
    min-height: 0 !important;
  }
  #root canvas[style*="height: 380px"] {
    height: 240px !important;
  }
  #root canvas[style*="height: 280px"] {
    height: 200px !important;
  }
}
`

// 注入移动端样式
if (typeof document !== 'undefined') {
  const existing = document.getElementById('dashboard-mobile-styles')
  if (!existing) {
    const styleEl = document.createElement('style')
    styleEl.id = 'dashboard-mobile-styles'
    styleEl.textContent = mobileStyles
    document.head.appendChild(styleEl)
  }
}

export default Dashboard
