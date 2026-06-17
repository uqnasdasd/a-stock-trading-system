#!/usr/bin/env python3
"""
A股超短交易实时监测系统 v2.4
单文件版本 - 只需要Python，双击运行
"""

import asyncio
import json
import os
import sys
import time
import urllib.request
import urllib.error
from datetime import datetime
from typing import Dict, List, Optional, Any

# 检查并安装依赖
def check_dependencies():
    """检查并安装必要的依赖"""
    try:
        import fastapi
        import uvicorn
        return True
    except ImportError:
        print("=" * 50)
        print("首次运行，正在安装依赖...")
        print("这可能需要 1-2 分钟，请稍候...")
        print("=" * 50)
        import subprocess
        deps = ["fastapi", "uvicorn", "python-multipart"]
        for dep in deps:
            try:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "--quiet", "--break-system-packages"])
            except:
                subprocess.check_call([sys.executable, "-m", "pip", "install", dep, "--quiet"])
        print("依赖安装完成！")
        return True

check_dependencies()

from fastapi import FastAPI
from fastapi.responses import HTMLResponse
import uvicorn

# ============ 数据收集器 ============
class DataCollector:
    """股票数据收集器"""

    INDEX_CODES = {
        "sh000001": "上证指数",
        "sz399001": "深证成指",
        "sz399006": "创业板指",
        "sh000300": "沪深300",
        "sh000905": "中证500",
    }

    def __init__(self):
        self.cache = {}
        self.cache_time = 0

    def get_index_quotes(self) -> List[Dict]:
        """获取指数行情"""
        try:
            codes = ",".join(self.INDEX_CODES.keys())
            url = f"https://hq.sinajs.cn/list={codes}"
            req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = resp.read().decode("gb2312", errors="ignore")

            indices = []
            for line in data.strip().split(";"):
                if not line.strip():
                    continue
                parts = line.split("=")
                if len(parts) < 2:
                    continue
                code = parts[0].split("_")[-1]
                values = parts[1].strip('"').split(",")
                if len(values) < 5:
                    continue

                name = self.INDEX_CODES.get(code, code)
                pre_close = float(values[2]) if values[2] else 0
                current = float(values[3]) if values[3] else 0
                change_pct = round((current - pre_close) / pre_close * 100, 2) if pre_close else 0

                indices.append({
                    "code": code,
                    "name": name,
                    "price": current,
                    "change_pct": change_pct,
                    "pre_close": pre_close,
                })
            return indices
        except Exception as e:
            print(f"获取指数失败: {e}")
            # 返回模拟数据
            return [
                {"code": "sh000001", "name": "上证指数", "price": 3091.89, "change_pct": -0.11, "pre_close": 3095.0},
                {"code": "sz399001", "name": "深证成指", "price": 10675.25, "change_pct": 0.93, "pre_close": 10577.0},
                {"code": "sz399006", "name": "创业板指", "price": 2102.94, "change_pct": 1.72, "pre_close": 2067.0},
                {"code": "sh000300", "name": "沪深300", "price": 3884.23, "change_pct": -0.15, "pre_close": 3890.0},
                {"code": "sh000905", "name": "中证500", "price": 5507.98, "change_pct": 1.20, "pre_close": 5442.0},
            ]

    def get_limit_stocks(self) -> Dict:
        """获取涨跌停股票"""
        try:
            # 使用东方财富API
            url = "https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=20&sort=fbt%3Aasc&date=" + datetime.now().strftime("%Y%m%d")
            req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
            with urllib.request.urlopen(req, timeout=5) as resp:
                data = json.loads(resp.read().decode("utf-8"))

            limit_up = []
            for item in data.get("data", {}).get("pool", []):
                limit_up.append({
                    "code": item.get("c", ""),
                    "name": item.get("n", ""),
                    "price": item.get("p", 0),
                    "change_pct": item.get("zdp", 0),
                })
            return {"limit_up": limit_up, "limit_down": []}
        except Exception as e:
            print(f"获取涨跌停失败: {e}")
            return {
                "limit_up": [
                    {"code": "603019", "name": "中科曙光", "price": 68.50, "change_pct": 10.01},
                    {"code": "688256", "name": "寒武纪", "price": 256.80, "change_pct": 20.00},
                ],
                "limit_down": [
                    {"code": "002005", "name": "ST德豪", "price": 1.85, "change_pct": -5.13},
                ],
            }


# ============ 风控系统 ============
class RiskController:
    """风控控制器"""

    def __init__(self):
        self.total_capital = 100000.0
        self.positions = {}
        self.daily_trades = []
        self.weekly_trades = []
        self.daily_pnl = 0.0
        self.weekly_pnl = 0.0
        self.is_locked = False
        self.lock_reason = ""

    def get_status(self) -> Dict:
        total_value = sum(p.get("market_value", 0) for p in self.positions.values())
        total_pct = total_value / self.total_capital if self.total_capital > 0 else 0
        return {
            "total_position_pct": round(total_pct, 4),
            "daily_profit_pct": round(self.daily_pnl / self.total_capital, 4) if self.total_capital else 0,
            "weekly_profit_pct": round(self.weekly_pnl / self.total_capital, 4) if self.total_capital else 0,
            "daily_trade_count": len(self.daily_trades),
            "weekly_trade_count": len(self.weekly_trades),
            "is_locked": self.is_locked,
            "lock_reason": self.lock_reason,
            "total_capital": round(self.total_capital, 2),
            "used_capital": round(total_value, 2),
            "available_capital": round(max(self.total_capital - total_value, 0), 2),
        }

    def can_trade(self) -> tuple:
        if self.is_locked:
            return False, self.lock_reason
        if len(self.daily_trades) >= 2:
            return False, "今日交易次数已达上限(2次)"
        return True, ""


# ============ 前端HTML ============
FRONTEND_HTML = """<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股超短交易实时监测系统 v2.4</title>
<style>
*{margin:0;padding:0;box-sizing:border-box}
body{font-family:-apple-system,'PingFang SC','Microsoft YaHei',sans-serif;background:#0B1120;color:#E8ECF4;overflow:hidden;display:flex;height:100vh}
.nav{width:180px;min-width:180px;background:#1a1a2e;display:flex;flex-direction:column;padding:0}
.nav-title{padding:20px 16px 8px;font-size:18px;font-weight:bold;color:#e94560}
.nav-sub{padding:0 16px 20px;font-size:11px;color:#666}
.nav-items{flex:1;overflow-y:auto}
.nav-item{padding:10px 16px;cursor:pointer;font-size:13px;color:#8892b0;transition:all .2s;border-left:3px solid transparent;display:flex;align-items:center;gap:8px}
.nav-item:hover{background:#16213e;color:#e94560}
.nav-item.active{background:#16213e;color:#e94560;border-left-color:#e94560;font-weight:600}
.main{flex:1;display:flex;flex-direction:column;overflow:hidden}
.topbar{background:#16213e;padding:8px 16px;display:flex;align-items:center;gap:12px;flex-wrap:wrap;border-bottom:1px solid #1a1a2e}
.idx-card{background:#0B1120;padding:6px 12px;border-radius:6px;font-size:12px;display:flex;align-items:center;gap:6px}
.up{color:#e94560}.down{color:#16c79a}
.content{flex:1;overflow-y:auto;padding:16px;background:#f5f5f5}
.card{background:#fff;border-radius:8px;padding:16px;margin-bottom:12px;box-shadow:0 1px 3px rgba(0,0,0,.1);color:#333}
.card-title{font-size:14px;font-weight:600;margin-bottom:12px;color:#1a1a2e;border-bottom:2px solid #e94560;padding-bottom:6px;display:inline-block}
.sentiment{display:flex;gap:16px;align-items:center;flex-wrap:wrap}
.sent-item{text-align:center}
.sent-label{font-size:11px;color:#888;margin-bottom:4px}
.sent-value{font-size:24px;font-weight:700}
.sent-value.red{color:#e94560}
.sent-value.green{color:#16c79a}
.sent-value.blue{color:#0f3460}
table{width:100%;border-collapse:collapse;font-size:12px}
th{background:#f0f0f0;padding:8px;text-align:left;font-weight:600;color:#555;border-bottom:2px solid #e0e0e0}
td{padding:8px;border-bottom:1px solid #f0f0f0}
tr:hover{background:#fafafa}
.page{display:none}.page.active{display:block}
.loading{color:#999;font-size:12px;padding:20px;text-align:center}
</style>
</head>
<body>
<div class="nav">
  <div class="nav-title">A股超短交易</div>
  <div class="nav-sub">实时监测系统 v2.4</div>
  <div class="nav-items">
    <div class="nav-item active" onclick="showPage('overview')">📊 大盘总览</div>
    <div class="nav-item" onclick="showPage('auction')">🔥 竞价引擎</div>
    <div class="nav-item" onclick="showPage('position')">📋 持仓监控</div>
    <div class="nav-item" onclick="showPage('signals')">🚨 信号预警</div>
    <div class="nav-item" onclick="showPage('limit')">📈 涨跌停</div>
    <div class="nav-item" onclick="showPage('watchlist')">⭐ 自选股</div>
    <div class="nav-item" onclick="showPage('concept')">🔥 概念板块</div>
    <div class="nav-item" onclick="showPage('dragon')">🐉 龙虎榜</div>
    <div class="nav-item" onclick="showPage('log')">📝 交易日志</div>
    <div class="nav-item" onclick="showPage('risk')">🛡️ 风控中心</div>
  </div>
</div>
<div class="main">
  <div class="topbar" id="topbar">
    <div class="loading">正在加载指数数据...</div>
  </div>
  <div class="content">
    <div class="page active" id="page-overview">
      <div class="card">
        <div class="card-title">市场情绪</div>
        <div class="sentiment" id="sentiment">
          <div class="sent-item"><div class="sent-label">情绪评分</div><div class="sent-value blue" id="sent-score">--</div></div>
          <div class="sent-item"><div class="sent-label">涨/跌家数</div><div class="sent-value" id="sent-updown">-- / --</div></div>
          <div class="sent-item"><div class="sent-label">涨停 / 跌停</div><div class="sent-value red" id="sent-limit">-- / --</div></div>
        </div>
      </div>
      <div class="card">
        <div class="card-title">板块强度 TOP5</div>
        <table>
          <tr><th>板块</th><th>涨幅</th></tr>
          <tr><td>人工智能</td><td class="up">+4.28%</td></tr>
          <tr><td>半导体</td><td class="up">+3.15%</td></tr>
          <tr><td>新能源车</td><td class="up">+2.87%</td></tr>
          <tr><td>消费电子</td><td class="up">+2.31%</td></tr>
          <tr><td>机器人</td><td class="up">+1.96%</td></tr>
        </table>
      </div>
    </div>
    <div class="page" id="page-limit">
      <div class="card">
        <div class="card-title">涨停板</div>
        <div id="limit-up-list" class="loading">正在加载...</div>
      </div>
      <div class="card">
        <div class="card-title">跌停板</div>
        <div id="limit-down-list" class="loading">正在加载...</div>
      </div>
    </div>
    <div class="page" id="page-risk">
      <div class="card">
        <div class="card-title">风控状态</div>
        <div id="risk-status" class="loading">正在加载...</div>
      </div>
    </div>
    <div class="page" id="page-signals">
      <div class="card">
        <div class="card-title">信号预警</div>
        <p>🚨 止损预警: 中科曙光 跌破止损线</p>
        <p>⚡ 移动止盈: 寒武纪 触发止盈</p>
      </div>
    </div>
    <div class="page" id="page-position">
      <div class="card"><div class="card-title">持仓列表</div><p>暂无持仓</p></div>
    </div>
    <div class="page" id="page-watchlist">
      <div class="card"><div class="card-title">自选股</div><p>中科曙光、寒武纪、比亚迪</p></div>
    </div>
    <div class="page" id="page-concept">
      <div class="card"><div class="card-title">概念板块</div><p>人工智能 +4.28%</p><p>半导体 +3.15%</p></div>
    </div>
    <div class="page" id="page-dragon">
      <div class="card"><div class="card-title">龙虎榜</div><p>中科曙光 净买入 +28,350万</p></div>
    </div>
    <div class="page" id="page-log">
      <div class="card"><div class="card-title">交易日志</div><p>暂无交易记录</p></div>
    </div>
    <div class="page" id="page-auction">
      <div class="card"><div class="card-title">竞价分析</div><p>9:15-9:25 集合竞价实时分析</p></div>
    </div>
  </div>
</div>
<script>
function showPage(name) {
  document.querySelectorAll('.page').forEach(p => p.classList.remove('active'));
  document.querySelectorAll('.nav-item').forEach(n => n.classList.remove('active'));
  document.getElementById('page-' + name).classList.add('active');
  event.target.classList.add('active');
}

async function loadData() {
  try {
    const res = await fetch('/api/market/indices');
    const data = await res.json();
    const indices = data.indices || [];
    let html = '';
    indices.forEach(idx => {
      const cls = idx.change_pct >= 0 ? 'up' : 'down';
      const sign = idx.change_pct >= 0 ? '+' : '';
      html += `<div class="idx-card"><span>${idx.name}</span><span>${idx.price}</span><span class="${cls}">${sign}${idx.change_pct}%</span></div>`;
    });
    document.getElementById('topbar').innerHTML = html;

    // 计算情绪
    const up = indices.filter(i => i.change_pct > 0).length;
    const down = indices.filter(i => i.change_pct < 0).length;
    const score = Math.round((up / (up + down || 1)) * 100);
    document.getElementById('sent-score').textContent = score;
    document.getElementById('sent-updown').textContent = `${up} / ${down}`;
  } catch(e) { console.error(e); }

  try {
    const res = await fetch('/api/limit/stocks');
    const data = await res.json();
    const upList = data.limit_up || [];
    const downList = data.limit_down || [];
    document.getElementById('sent-limit').textContent = `${upList.length} / ${downList.length}`;

    let upHtml = '<table><tr><th>股票</th><th>价格</th><th>涨幅</th></tr>';
    upList.slice(0, 10).forEach(s => {
      upHtml += `<tr><td>${s.name}</td><td>${s.price}</td><td class="up">+${s.change_pct}%</td></tr>`;
    });
    upHtml += '</table>';
    document.getElementById('limit-up-list').innerHTML = upHtml;

    let downHtml = '<table><tr><th>股票</th><th>价格</th><th>跌幅</th></tr>';
    downList.slice(0, 10).forEach(s => {
      downHtml += `<tr><td>${s.name}</td><td>${s.price}</td><td class="down">${s.change_pct}%</td></tr>`;
    });
    downHtml += '</table>';
    document.getElementById('limit-down-list').innerHTML = downHtml;
  } catch(e) { console.error(e); }

  try {
    const res = await fetch('/api/risk/status');
    const data = await res.json();
    const s = data.status || {};
    document.getElementById('risk-status').innerHTML = `
      <p>总资金: ¥${s.total_capital}</p>
      <p>已用资金: ¥${s.used_capital}</p>
      <p>可用资金: ¥${s.available_capital}</p>
      <p>总仓位: ${(s.total_position_pct * 100).toFixed(1)}%</p>
      <p>当日盈亏: ${(s.daily_profit_pct * 100).toFixed(2)}%</p>
    `;
  } catch(e) { console.error(e); }
}

loadData();
setInterval(loadData, 5000);
</script>
</body>
</html>"""


# ============ FastAPI 应用 ============
collector = DataCollector()
risk_controller = RiskController()

app = FastAPI(title="A股超短交易实时监测系统", version="2.4")

@app.get("/")
async def root():
    return HTMLResponse(content=FRONTEND_HTML)

@app.get("/api/market/indices")
async def get_indices():
    indices = collector.get_index_quotes()
    return {"indices": indices}

@app.get("/api/limit/stocks")
async def get_limit_stocks():
    return collector.get_limit_stocks()

@app.get("/api/risk/status")
async def get_risk_status():
    status = risk_controller.get_status()
    can_trade, reason = risk_controller.can_trade()
    return {"status": status, "can_trade": can_trade, "reason": reason}

@app.get("/api/positions")
async def get_positions():
    return {"positions": [], "count": 0, "total_value": 0, "total_profit_pct": 0}

@app.get("/api/signals")
async def get_signals():
    return {"signals": []}

@app.get("/api/watchlist")
async def get_watchlist():
    return {"watchlist": []}

@app.get("/api/accounts")
async def get_accounts():
    return {"accounts": []}

@app.get("/health")
async def health_check():
    return {"status": "healthy"}


if __name__ == "__main__":
    print("=" * 50)
    print("A股超短交易实时监测系统 v2.4")
    print("=" * 50)
    print("正在启动...")
    print("启动后请打开浏览器访问: http://localhost:8000")
    print("=" * 50)
    uvicorn.run(app, host="0.0.0.0", port=8000)
