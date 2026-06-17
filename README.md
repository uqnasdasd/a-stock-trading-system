# A股超短交易实时监测系统 v2.4

## 在线演示（手机/电脑直接打开）

**点击下方链接，无需安装，直接查看：**

👉 [A股超短交易实时监测系统 - 在线演示](https://htmlpreview.github.io/?https://github.com/uqnasdasd/a-stock-trading-system/blob/main/a-stock-trading-demo.html)

或者复制这个链接到浏览器：
```
https://htmlpreview.github.io/?https://github.com/uqnasdasd/a-stock-trading-system/blob/main/a-stock-trading-demo.html
```

---

## 本地安装（完整版带实时数据）

### 只需要装 Python！

1. **安装 Python 3.10+**
   - 打开 https://www.python.org/downloads/
   - 下载安装，**务必勾选 "Add Python to PATH"**

2. **下载代码**
   - 打开 https://github.com/uqnasdasd/a-stock-trading-system
   - 点击 Code → Download ZIP
   - 解压到桌面

3. **双击 start.bat**
   - 首次运行会自动安装依赖
   - 浏览器自动打开 http://localhost:8000

---

## 功能模块

- 📊 大盘总览（指数/情绪/板块/龙头）
- 🔥 竞价引擎（9:15-9:25实时分析）
- 📋 持仓监控（止损/止盈/移动止盈）
- 🚨 信号预警（开盘确认/早盘突破/尾盘稳健）
- 📈 涨跌停监控（全A股5000+）
- ⭐ 自选股管理
- 🔥 概念板块追踪
- 🐉 龙虎榜数据
- 📝 交易日志
- 🛡️ 风控中心
- 📉 策略回测
- ⏸ 历史数据回放

---

## 更新日志

### v2.4 (2026-06-17)
- 修复后端启动问题
- 简化安装流程（只需Python）
- 添加在线演示版
- 修复风控API字段缺失
- 修复bat文件换行符问题

### v2.3 (2026-06-16)
- 添加accounts API和数据库表
- 修复ConceptPanel/DragonTiger导航
- 修复数据流不通问题

### v2.2 (2026-06-16)
- 修复HTTPException导入
- 修复useMarketData数据请求
- 修复Dashboard字段映射

### v2.1 (2026-06-16)
- 数据源容错切换（新浪/腾讯/东方财富）
- 涨跌停覆盖全部A股5000+
- 动态板块映射
- 风控数据持久化
- 移动止盈修复
- 开盘确认/早盘突破/尾盘稳健信号
- 策略回测后端
- 历史数据回放
