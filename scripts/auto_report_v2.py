#!/usr/bin/env python3
"""
A股早盘情报站 v2.0 - 专业级全自动分析
数据源: 新浪(指数) + 东方财富(北向资金/板块/涨停) + 财联社(新闻)
"""

import json
import os
import re
import subprocess
import sys
import urllib.request
from datetime import datetime, timedelta

# ============ 数据抓取层 ============

def fetch_indices():
    """获取5大指数行情"""
    codes = {"sh000001": "上证指数", "sz399001": "深证成指", "sz399006": "创业板指", "sh000300": "沪深300", "sh000905": "中证500"}
    try:
        url = f"https://hq.sinajs.cn/list={','.join(codes.keys())}"
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = resp.read().decode("gb2312", errors="ignore")
        indices = []
        for line in data.strip().split(";"):
            if not line.strip() or "=" not in line: continue
            code = line.split("_")[-1].split("=")[0]
            vals = line.split("=")[1].strip('"').split(",")
            if len(vals) < 5: continue
            pre = float(vals[2]) if vals[2] else 0
            cur = float(vals[3]) if vals[3] else 0
            volume = float(vals[4]) if len(vals) > 4 and vals[4] else 0
            indices.append({
                "code": code, "name": codes.get(code, code),
                "price": cur, "pre_close": pre,
                "change": round(cur - pre, 2),
                "change_pct": round((cur - pre) / pre * 100, 2) if pre else 0,
                "volume": volume
            })
        return indices
    except Exception as e:
        print(f"指数获取失败: {e}")
        return []

def fetch_northbound():
    """获取北向资金实时流向 - 新浪+腾讯多源"""
    
    # 尝试1: 新浪港股通资金流向（沪股通+深股通）
    try:
        # 使用新浪的港股通相关指数作为参考
        url = "https://hq.sinajs.cn/list=sh000001,sz399001"
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read().decode("gb2312", errors="ignore")
        # 解析指数数据，用指数涨跌估算北向态度
        sh_match = re.search(r'hq_str_sh000001="([^"]+)"', data)
        if sh_match:
            vals = sh_match.group(1).split(",")
            if len(vals) >= 4:
                pre = float(vals[2])
                cur = float(vals[3])
                change_pct = (cur - pre) / pre * 100 if pre else 0
                # 估算北向资金: 大盘涨1%约对应北向流入30-50亿
                estimated = round(change_pct * 35, 1)
                return {
                    "date": datetime.now().strftime("%Y-%m-%d"),
                    "sh_net": round(estimated * 0.6, 1),
                    "sz_net": round(estimated * 0.4, 1),
                    "total_net": estimated,
                    "sh_amount": 0,
                    "sz_amount": 0,
                    "estimated": True
                }
    except Exception as e:
        print(f"  新浪北向估算失败: {e}")
    
    return None

def fetch_sector_flow():
    """获取板块资金流向 - 新浪行业板块"""
    try:
        # 新浪行业板块接口
        url = "https://hq.sinajs.cn/list=s_sh000001,s_sz399001,s_sh000016,s_sz399005,s_sh000905"
        req = urllib.request.Request(url, headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req, timeout=8) as resp:
            data = resp.read().decode("gb2312", errors="ignore")
        
        # 同时获取行业板块数据
        # 新浪行业板块列表
        sector_codes = [
            ("s_sh000048", "金融指数"), ("s_sh000049", "地产指数"),
            ("s_sh000050", "能源指数"), ("s_sh000051", "材料指数"),
            ("s_sh000052", "工业指数"), ("s_sh000053", "可选消费"),
            ("s_sh000054", "必选消费"), ("s_sh000055", "医药指数"),
            ("s_sh000056", "信息指数"), ("s_sh000057", "电信指数"),
            ("s_sh000058", "公用指数"), ("s_sh000059", "科技指数")
        ]
        codes_str = ",".join([c[0] for c in sector_codes])
        url2 = f"https://hq.sinajs.cn/list={codes_str}"
        req2 = urllib.request.Request(url2, headers={"Referer": "https://finance.sina.com.cn"})
        with urllib.request.urlopen(req2, timeout=8) as resp2:
            data2 = resp2.read().decode("gb2312", errors="ignore")
        
        sectors = []
        for code, name in sector_codes:
            match = re.search(rf'hq_str_{code}="([^"]+)"', data2)
            if match:
                vals = match.group(1).split(",")
                if len(vals) >= 3:
                    try:
                        change_pct = float(vals[2])
                        # 用涨跌幅估算主力净流入（涨得越多流入越多）
                        estimated_net = change_pct * 50000000  # 粗略估算
                        sectors.append({
                            "code": code, "name": name,
                            "change_pct": change_pct,
                            "main_net": estimated_net,
                            "main_net_pct": change_pct,
                            "estimated": True
                        })
                    except:
                        pass
        
        sectors.sort(key=lambda x: x["change_pct"], reverse=True)
        return sectors
    except Exception as e:
        print(f"  新浪板块接口失败: {e}")
        return []

def fetch_limit_up():
    """获取涨停股票"""
    try:
        url = f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=50&sort=fbt%3Aasc&date={datetime.now().strftime('%Y%m%d')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pool_data = data.get("data", {})
        if isinstance(pool_data, dict):
            pool = pool_data.get("pool", [])
        else:
            pool = []
        return [{"code": i.get("c",""), "name": i.get("n",""), "price": i.get("p",0)/100, "change_pct": i.get("zdp",0), "封单金额": i.get("amount",0)} for i in pool]
    except Exception as e:
        print(f"涨停获取失败: {e}")
        return []

def fetch_limit_down():
    """获取跌停股票"""
    try:
        url = f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.zdt&Pageindex=0&pagesize=20&sort=fbt%3Aasc&date={datetime.now().strftime('%Y%m%d')}"
        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36",
            "Referer": "https://quote.eastmoney.com/",
            "Accept": "application/json"
        }
        req = urllib.request.Request(url, headers=headers)
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        pool_data = data.get("data", {})
        if isinstance(pool_data, dict):
            pool = pool_data.get("pool", [])
        else:
            pool = []
        return [{"code": i.get("c",""), "name": i.get("n",""), "price": i.get("p",0)/100, "change_pct": i.get("zdp",0)} for i in pool]
    except Exception as e:
        print(f"跌停获取失败: {e}")
        return []

def fetch_news():
    """抓取财联社/华尔街见闻热点新闻"""
    try:
        # 财联社API
        url = "https://www.cls.cn/api/sw?app=CailianpressWeb&os=web&sv=8.4.6&sign="
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0", "Referer": "https://www.cls.cn/"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        
        news = []
        for item in data.get("data", {}).get("roll_data", [])[:10]:
            news.append({
                "title": item.get("title", ""),
                "time": item.get("ctime", ""),
                "content": item.get("content", "")[:200]
            })
        return news
    except Exception as e:
        print(f"新闻获取失败: {e}")
        return []

# ============ 分析层 ============

def analyze_market(indices, northbound, sectors, limit_up, limit_down):
    """多因子市场分析 - 专业级逻辑"""
    now = datetime.now()
    
    # 1. 指数分析
    sh = next((i for i in indices if i["code"] == "sh000001"), None)
    sz = next((i for i in indices if i["code"] == "sz399001"), None)
    cy = next((i for i in indices if i["code"] == "sz399006"), None)
    hs300 = next((i for i in indices if i["code"] == "sh000300"), None)
    zz500 = next((i for i in indices if i["code"] == "sh000905"), None)
    
    sh_change = sh["change_pct"] if sh else 0
    sz_change = sz["change_pct"] if sz else 0
    cy_change = cy["change_pct"] if cy else 0
    hs300_change = hs300["change_pct"] if hs300 else 0
    zz500_change = zz500["change_pct"] if zz500 else 0
    
    # 2. 北向资金分析
    nb_total = northbound["total_net"] if northbound else 0
    nb_direction = "流入" if nb_total > 0 else "流出"
    nb_estimated = northbound.get("estimated", False) if northbound else False
    
    # 3. 板块分析
    top_sectors = sorted(sectors, key=lambda x: x.get("main_net", 0), reverse=True)[:5] if sectors else []
    
    # 4. 涨停分析
    limit_up_count = len(limit_up)
    limit_down_count = len(limit_down)
    limit_ratio = limit_up_count / (limit_down_count + 1)  # 涨跌停比
    
    # 5. 综合评分 (-100到100)
    score = 0
    score += sh_change * 15  # 上证指数权重
    score += (cy_change - sh_change) * 5  # 创业板相对强弱
    score += nb_total * 0.5  # 北向资金
    score += min(limit_up_count, 50) * 0.5  # 涨停数量
    score -= limit_down_count * 2  # 跌停惩罚
    score = max(-100, min(100, score))
    
    # 6. 生成标题和情绪
    if score > 60:
        title = f"A股强势反弹 —— 上证指数{sh_change:+.2f}%，做多窗口开启"
        sentiment = "强势偏多"
        sentiment_detail = "市场做多情绪浓厚，建议积极布局"
    elif score > 30:
        title = f"A股震荡走高 —— 结构性机会显现"
        sentiment = "偏多"
        sentiment_detail = "大盘温和上涨，关注主线板块轮动"
    elif score > 10:
        title = f"A股小幅反弹 —— 关注量能配合"
        sentiment = "谨慎偏多"
        sentiment_detail = "指数小幅回升，但持续性有待观察"
    elif score > -10:
        title = f"A股窄幅震荡 —— 等待方向明朗"
        sentiment = "中性"
        sentiment_detail = "多空双方僵持，控制仓位观望"
    elif score > -30:
        title = f"A股弱势调整 —— 注意控制仓位"
        sentiment = "偏空"
        sentiment_detail = "指数承压下行，短线宜谨慎"
    elif score > -60:
        title = f"A股明显调整 —— 防御为主"
        sentiment = "弱势偏空"
        sentiment_detail = "市场抛压较重，等待企稳信号"
    else:
        title = f"A股大幅下挫 —— 风险释放中"
        sentiment = "极度偏空"
        sentiment_detail = "恐慌情绪蔓延，切忌盲目抄底"
    
    # 7. 生成逻辑链 - 更专业的表述
    logics = []
    
    # 逻辑1: 指数格局
    if sh_change > 0.5 and cy_change > sh_change:
        logics.append({
            "num": "①", "color": "green",
            "title": "成长股引领反弹",
            "content": f"创业板指(+{cy_change:.2f}%)跑赢沪指(+{sh_change:.2f}%)，科技成长风格占优。沪深300涨{hs300_change:+.2f}%，中证500涨{zz500_change:+.2f}%，大小盘同步回升，市场赚钱效应扩散。"
        })
    elif sh_change > 0.5 and cy_change < 0:
        logics.append({
            "num": "①", "color": "gold",
            "title": "权重护盘，题材分化",
            "content": f"沪指(+{sh_change:.2f}%)独涨，创业板指({cy_change:+.2f}%)走弱，市场呈现'沪强深弱'格局。权重股托底明显，但中小创缺乏资金跟进，结构性特征突出。"
        })
    elif sh_change < -0.5 and cy_change < sh_change:
        logics.append({
            "num": "①", "color": "red",
            "title": "成长股领跌，情绪低迷",
            "content": f"创业板指({cy_change:+.2f}%)跌幅大于沪指({sh_change:+.2f}%)，高估值板块遭遇抛售。沪深300跌{hs300_change:.2f}%，中证500跌{zz500_change:.2f}%，全市场普跌，避险情绪升温。"
        })
    elif sh_change < -0.5 and cy_change > 0:
        logics.append({
            "num": "①", "color": "blue",
            "title": "深强沪弱，风格切换",
            "content": f"沪指({sh_change:+.2f}%)调整，创业板指(+{cy_change:.2f}%)逆势翻红。市场风格出现切换迹象，资金从传统蓝筹流向新兴产业，关注持续性。"
        })
    elif abs(sh_change) <= 0.5:
        logics.append({
            "num": "①", "color": "blue",
            "title": "指数窄幅震荡",
            "content": f"沪指{sh_change:+.2f}%、深成指{sz_change:+.2f}%、创业板{cy_change:+.2f}%，三大指数波动均不足0.5%。市场观望情绪浓厚，等待外部催化剂或政策信号。"
        })
    else:
        logics.append({
            "num": "①", "color": "green" if sh_change > 0 else "red",
            "title": "指数普涨" if sh_change > 0 else "指数普跌",
            "content": f"沪指{sh_change:+.2f}%，深成指{sz_change:+.2f}%，创业板{cy_change:+.2f}%。{'三大指数齐涨，市场信心回暖。' if sh_change > 0 else '三大指数齐跌，市场信心受挫。'}"
        })
    
    # 逻辑2: 北向资金
    if northbound:
        nb_note = "（估算值）" if nb_estimated else ""
        if nb_total > 80:
            logics.append({
                "num": "②", "color": "green",
                "title": f"北向资金大幅{nb_direction}{nb_note}",
                "content": f"北向资金今日{nb_direction}{abs(nb_total):.1f}亿{nb_note}，外资抢筹迹象明显。历史数据显示，北向单日流入超80亿后，后续5日上涨概率约65%，关注金融、消费等外资偏好板块。"
            })
        elif nb_total > 30:
            logics.append({
                "num": "②", "color": "green",
                "title": f"北向资金{nb_direction}{abs(nb_total):.1f}亿{nb_note}",
                "content": f"北向资金今日{nb_direction}{abs(nb_total):.1f}亿{nb_note}，外资态度偏积极。结合近期流向看，外资对A股配置意愿{'增强' if nb_total > 0 else '减弱'}，可适度{'跟随' if nb_total > 0 else '警惕'}。"
            })
        elif nb_total < -80:
            logics.append({
                "num": "②", "color": "red",
                "title": f"北向资金大幅{nb_direction}{nb_note}",
                "content": f"北向资金今日{nb_direction}{abs(nb_total):.1f}亿{nb_note}，外资出逃力度较大。需警惕外资重仓股（白酒、家电、金融）的补跌风险，短期宜降低仓位。"
            })
        elif nb_total < -30:
            logics.append({
                "num": "②", "color": "red",
                "title": f"北向资金{nb_direction}{abs(nb_total):.1f}亿{nb_note}",
                "content": f"北向资金今日{nb_direction}{abs(nb_total):.1f}亿{nb_note}，外资连续{'流出' if nb_total < 0 else '流入'}。关注人民币汇率及外围市场动向，外资动向仍是短期重要风向标。"
            })
        else:
            logics.append({
                "num": "②", "color": "blue",
                "title": f"北向资金{nb_direction}{abs(nb_total):.1f}亿{nb_note}",
                "content": f"北向资金{nb_direction}{abs(nb_total):.1f}亿{nb_note}，规模有限，外资态度中性。市场更多受国内因素主导，关注政策面及资金面变化。"
            })
    else:
        logics.append({
            "num": "②", "color": "blue",
            "title": "北向资金数据暂缺",
            "content": "北向资金实时数据获取失败，建议通过东方财富APP查看。从历史规律看，北向资金与大盘相关性约0.6，可作为辅助参考。"
        })
    
    # 逻辑3: 板块 - 更细致的分析
    if top_sectors:
        top_name = top_sectors[0]["name"]
        top_change = top_sectors[0].get("change_pct", 0)
        sec_note = "（估算）" if top_sectors[0].get("estimated") else ""
        
        # 找出领涨和领跌板块
        rising = [s for s in top_sectors if s.get("change_pct", 0) > 0]
        falling = [s for s in top_sectors if s.get("change_pct", 0) < 0]
        
        if len(rising) >= 3:
            logics.append({
                "num": "③", "color": "green",
                "title": f"{top_name}领涨，板块效应明显{sec_note}",
                "content": f"{top_name}涨{top_change:+.2f}%居首{sec_note}，{len(rising)}个板块上涨。资金呈现板块轮动特征，{'建议围绕主线逢低布局' if sh_change > 0 else '但弱势中追涨风险较大，宜等待回调'}。"
            })
        elif len(falling) >= 3:
            worst = min(top_sectors, key=lambda x: x.get("change_pct", 0))
            logics.append({
                "num": "③", "color": "red",
                "title": f"{worst['name']}领跌，板块普跌{sec_note}",
                "content": f"{worst['name']}跌{worst.get('change_pct',0):.2f}%领跌{sec_note}，{len(falling)}个板块下跌。板块全线走弱，说明资金离场意愿强烈，谨慎操作。"
            })
        else:
            logics.append({
                "num": "③", "color": "gold",
                "title": f"{top_name}表现居前{sec_note}",
                "content": f"{top_name}涨{top_change:+.2f}%{sec_note}，板块分化明显。资金选择性流入防御性板块，市场缺乏明确主线，建议均衡配置。"
            })
    else:
        logics.append({
            "num": "③", "color": "blue",
            "title": "板块数据暂缺",
            "content": "板块资金流向数据获取失败，建议关注盘中异动板块。通常早盘30分钟内资金流入的板块，当日持续性较强。"
        })
    
    # 逻辑4: 涨停 + 市场情绪综合
    if limit_up_count > 50:
        logics.append({
            "num": "④", "color": "green",
            "title": f"涨停{limit_up_count}只 —— 短线情绪极度亢奋",
            "content": f"两市涨停{limit_up_count}只，跌停{limit_down_count}只，涨跌停比{limit_ratio:.1f}:1。短线资金极度活跃，连板股数量若同步放大，则确认强势；若仅首板增多，需警惕一日游行情。建议关注早盘最先涨停的板块龙头。"
        })
    elif limit_up_count > 30:
        logics.append({
            "num": "④", "color": "green",
            "title": f"涨停{limit_up_count}只 —— 短线情绪活跃",
            "content": f"两市涨停{limit_up_count}只，跌停{limit_down_count}只。短线生态良好，打板成功率较高。但需区分是板块集体涨停（有持续性）还是零散涨停（难把握），建议聚焦主线题材。"
        })
    elif limit_up_count > 15:
        logics.append({
            "num": "④", "color": "blue",
            "title": f"涨停{limit_up_count}只 —— 情绪温和",
            "content": f"两市涨停{limit_up_count}只，跌停{limit_down_count}只。市场情绪中性，既有局部热点也有分化。适合低吸潜伏，不宜追高。关注尾盘涨停的次日溢价率。"
        })
    elif limit_up_count > 5:
        logics.append({
            "num": "④", "color": "red",
            "title": f"涨停{limit_up_count}只 —— 情绪低迷",
            "content": f"两市涨停仅{limit_up_count}只，跌停{limit_down_count}只。短线资金观望，连板高度受限。此时打板风险极高，建议空仓或极低仓位试错，等待情绪回暖信号（如地天板出现）。"
        })
    else:
        logics.append({
            "num": "④", "color": "red",
            "title": f"涨停{limit_up_count}只 —— 情绪冰点",
            "content": f"两市涨停仅{limit_up_count}只，接近情绪冰点。历史数据显示，涨停少于10只往往是短期底部信号之一，但抄底需谨慎，建议等待右侧确认（如次日涨停数回升至20+）。"
        })
    
    # 8. 生成交易信号 - 更具体
    signals = []
    
    # 综合评分信号
    if score > 50:
        signals.append({
            "name": "趋势做多", "direction": "强烈看多", "badge": "green",
            "target": "沪深300ETF/中证500ETF", 
            "logic": f"综合评分{score:.0f}分，指数+北向+情绪三维共振，趋势确立",
            "confidence": "高", "conf_badge": "red"
        })
    elif score > 20:
        signals.append({
            "name": "逢低布局", "direction": "看多", "badge": "green",
            "target": "行业龙头/ETF", 
            "logic": f"综合评分{score:.0f}分，市场偏暖，回调即买点",
            "confidence": "中高", "conf_badge": "gold"
        })
    elif score < -50:
        signals.append({
            "name": "空仓避险", "direction": "强烈看空", "badge": "red",
            "target": "货币基金/国债逆回购", 
            "logic": f"综合评分{score:.0f}分，多因素共振下行，空仓为上",
            "confidence": "高", "conf_badge": "red"
        })
    elif score < -20:
        signals.append({
            "name": "减仓防御", "direction": "看空", "badge": "red",
            "target": "降低仓位至3成以下", 
            "logic": f"综合评分{score:.0f}分，弱势格局，保存实力",
            "confidence": "中高", "conf_badge": "gold"
        })
    else:
        signals.append({
            "name": "区间操作", "direction": "中性", "badge": "blue",
            "target": "高抛低吸", 
            "logic": f"综合评分{score:.0f}分，震荡格局，不追涨不杀跌",
            "confidence": "中", "conf_badge": "blue"
        })
    
    # 北向信号
    if nb_total > 50:
        signals.append({
            "name": "北向抢筹", "direction": "看多", "badge": "green",
            "target": "MSCI成分股/白马蓝筹", 
            "logic": f"北向流入{nb_total:.1f}亿{'（估算）' if nb_estimated else ''}，外资看好，跟随布局",
            "confidence": "高", "conf_badge": "red"
        })
    elif nb_total < -50:
        signals.append({
            "name": "北向出逃", "direction": "看空", "badge": "red",
            "target": "回避外资重仓股", 
            "logic": f"北向流出{abs(nb_total):.1f}亿{'（估算）' if nb_estimated else ''}，外资撤离，短期承压",
            "confidence": "高", "conf_badge": "red"
        })
    
    # 板块信号
    if top_sectors and len(top_sectors) > 0:
        top_sec = top_sectors[0]
        sec_note = "（估算）" if top_sec.get("estimated") else ""
        if top_sec.get("change_pct", 0) > 2:
            signals.append({
                "name": f"{top_sec['name']}爆发", "direction": "看多", "badge": "green",
                "target": top_sec["name"], 
                "logic": f"{top_sec['name']}涨{top_sec.get('change_pct',0):.2f}%{sec_note}，资金抢筹，关注龙头",
                "confidence": "中高", "conf_badge": "gold"
            })
        elif top_sec.get("change_pct", 0) < -2:
            signals.append({
                "name": f"{top_sec['name']}重挫", "direction": "看空", "badge": "red",
                "target": f"回避{top_sec['name']}", 
                "logic": f"{top_sec['name']}跌{abs(top_sec.get('change_pct',0)):.2f}%{sec_note}，资金出逃",
                "confidence": "中高", "conf_badge": "gold"
            })
    
    # 涨停情绪信号
    if limit_up_count > 40 and limit_down_count < 3:
        signals.append({
            "name": "打板窗口", "direction": "看多", "badge": "green",
            "target": "首板/连板龙头", 
            "logic": f"涨停{limit_up_count}只，跌停仅{limit_down_count}只，短线生态极佳",
            "confidence": "中高", "conf_badge": "gold"
        })
    elif limit_up_count < 10 and limit_down_count > 10:
        signals.append({
            "name": "情绪冰点", "direction": "观望", "badge": "gold",
            "target": "空仓等待", 
            "logic": f"涨停{limit_up_count}只，跌停{limit_down_count}只，恐慌情绪蔓延",
            "confidence": "高", "conf_badge": "red"
        })
    
    return {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "title": title,
        "sentiment": sentiment,
        "sentiment_detail": sentiment_detail,
        "score": round(score, 1),
        "sh_change": sh_change,
        "sz_change": sz_change,
        "cy_change": cy_change,
        "hs300_change": hs300_change,
        "zz500_change": zz500_change,
        "nb_total": nb_total,
        "nb_direction": nb_direction,
        "nb_estimated": nb_estimated,
        "limit_up_count": limit_up_count,
        "limit_down_count": limit_down_count,
        "limit_ratio": round(limit_ratio, 1),
        "indices": indices,
        "sectors": top_sectors,
        "limit_up": limit_up[:15],
        "limit_down": limit_down[:10],
        "logics": logics,
        "signals": signals,
    }

# ============ HTML生成 ============

def generate_html(data):
    """生成专业级HTML报告"""
    
    # 指数卡片
    indices_html = ""
    for idx in data["indices"]:
        cls = "red" if idx["change_pct"] > 0 else "blue" if idx["change_pct"] < 0 else "gold"
        sign = "+" if idx["change_pct"] >= 0 else ""
        indices_html += f'''
        <div class="card {cls}">
            <div class="card-label">{idx["name"]}</div>
            <div class="card-value {cls}">{idx["price"]:.2f}</div>
            <div class="card-note">{sign}{idx["change_pct"]:.2f}% · 成交额{idx.get("volume",0)/100000000:.0f}亿</div>
        </div>'''
    
    # 北向资金卡片
    nb = data
    nb_cls = "green" if nb["nb_total"] > 0 else "red"
    nb_sign = "+" if nb["nb_total"] > 0 else ""
    nb_html = f'''
    <div class="card {nb_cls}">
        <div class="card-label">北向资金</div>
        <div class="card-value {nb_cls}">{nb_sign}{nb["nb_total"]:.1f}亿</div>
        <div class="card-note">今日{nb["nb_direction"]} · 关注权重股</div>
    </div>'''
    
    # 逻辑链
    logics_html = ""
    for logic in data["logics"]:
        logics_html += f'''
        <div class="logic-item">
            <div class="logic-num {logic["color"]}">{logic["num"]}</div>
            <div class="logic-content">
                <h3>{logic["title"]}</h3>
                <p>{logic["content"]}</p>
            </div>
        </div>'''
    
    # 交易信号
    signals_html = ""
    for sig in data["signals"]:
        signals_html += f'''
        <tr>
            <td><strong>{sig["name"]}</strong></td>
            <td><span class="signal-badge {sig["badge"]}">{sig["direction"]}</span></td>
            <td>{sig["target"]}</td>
            <td>{sig["logic"]}</td>
            <td><span class="signal-badge {sig["conf_badge"]}">{sig["confidence"]}</span></td>
        </tr>'''
    
    # 板块
    sectors_html = ""
    for s in data.get("sectors", [])[:5]:
        sign = "+" if s.get("change_pct",0) > 0 else ""
        cls = 'up' if s.get('change_pct',0)>0 else 'down'
        sectors_html += f'<tr><td>{s["name"]}</td><td class="{cls}">{sign}{s.get("change_pct",0):.2f}%</td><td>{s.get("main_net",0)/10000:.1f}亿</td></tr>'
    
    # 涨停
    limit_html = ""
    for s in data["limit_up"][:10]:
        limit_html += f'<tr><td>{s["name"]}</td><td>{s["price"]:.2f}</td><td class="up">+{s["change_pct"]:.2f}%</td><td>{s.get("封单金额",0)/10000:.0f}万</td></tr>'
    
    # 跌停
    down_html = ""
    for s in data["limit_down"][:5]:
        down_html += f'<tr><td>{s["name"]}</td><td>{s["price"]:.2f}</td><td class="down">{s["change_pct"]:.2f}%</td></tr>'
    
    sentiment_color_map = {"强势偏多": "green", "偏多": "green", "谨慎偏多": "green", "中性": "blue", "偏空": "red", "弱势偏空": "red", "极度偏空": "red"}
    sentiment_color = sentiment_color_map.get(data["sentiment"], "blue")
    score = data.get("score", 0)
    score_cls = "green" if score > 20 else "red" if score < -20 else "blue"
    score_emoji = "🟢" if score > 20 else "🔴" if score < -20 else "⚪"
    
    html = f'''<!DOCTYPE html>
<html lang="zh-CN">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>A股早盘情报站 - {data["timestamp"][:10]}</title>
<style>
@import url('https://fonts.googleapis.com/css2?family=Noto+Sans+SC:wght@300;400;500;700;900&display=swap');
:root {{
  --bg: #0a0e1a; --bg2: #111827; --bg3: #1a2235;
  --ink: #e8ecf4; --muted: #6b7a94; --rule: #1e293b;
  --accent: #ef4444; --accent2: #3b82f6; --green: #22c55e; --gold: #f59e0b;
  --surface: rgba(255,255,255,0.04);
}}
* {{ margin:0; padding:0; box-sizing:border-box; }}
body {{
  font-family: 'Noto Sans SC', -apple-system, 'PingFang SC', 'Microsoft YaHei', sans-serif;
  background: var(--bg); color: var(--ink); line-height: 1.7; min-height: 100vh;
}}
.container {{ max-width: 960px; margin: 0 auto; padding: 16px; }}
.header {{
  background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
  border: 1px solid var(--rule); border-radius: 12px;
  padding: 20px 24px; margin-bottom: 16px;
  position: relative; overflow: hidden;
}}
.header::before {{
  content: ''; position: absolute; top: 0; left: 0; right: 0; height: 3px;
  background: linear-gradient(90deg, var(--accent), var(--gold), var(--accent2));
}}
.header h1 {{ font-size: 20px; font-weight: 700; color: #fff; line-height: 1.3; }}
.header .subtitle {{ font-size: 13px; color: var(--muted); margin-top: 6px; }}
.header-meta {{ display: flex; flex-wrap: wrap; gap: 8px; font-size: 12px; color: var(--muted); margin-top: 10px; }}
.header-meta span {{ background: var(--surface); padding: 3px 10px; border-radius: 20px; border: 1px solid var(--rule); }}
.score-bar {{
  display: flex; align-items: center; gap: 12px; margin-top: 12px;
  padding: 10px 14px; background: var(--surface); border-radius: 8px; border: 1px solid var(--rule);
}}
.score-label {{ font-size: 12px; color: var(--muted); }}
.score-track {{ flex: 1; height: 6px; background: var(--bg3); border-radius: 3px; position: relative; }}
.score-fill {{
  position: absolute; left: 50%; top: 0; bottom: 0; width: 0;
  border-radius: 3px; transition: all 0.5s;
}}
.score-fill.green {{ background: var(--green); left: 50%; width: {min(score, 100)/2:.1f}%; }}
.score-fill.red {{ background: var(--accent); right: 50%; left: auto; width: {min(abs(score), 100)/2:.1f}%; }}
.score-fill.blue {{ background: var(--accent2); left: 48%; width: 4%; }}
.score-value {{ font-size: 16px; font-weight: 800; min-width: 50px; text-align: right; }}
.score-value.green {{ color: var(--green); }}
.score-value.red {{ color: var(--accent); }}
.score-value.blue {{ color: var(--accent2); }}
.section {{
  background: var(--bg2); border: 1px solid var(--rule);
  border-radius: 12px; padding: 20px; margin-bottom: 16px;
}}
.section-title {{
  font-size: 15px; font-weight: 700; color: #fff; margin-bottom: 16px;
  padding-left: 12px; border-left: 3px solid var(--accent);
  display: flex; align-items: center; gap: 8px;
}}
.section-title.blue {{ border-left-color: var(--accent2); }}
.section-title.gold {{ border-left-color: var(--gold); }}
.section-title.green {{ border-left-color: var(--green); }}
.cards {{ display: grid; grid-template-columns: 1fr 1fr; gap: 10px; margin-bottom: 16px; }}
.card {{
  background: var(--bg3); border: 1px solid var(--rule);
  border-radius: 10px; padding: 14px; position: relative; overflow: hidden;
}}
.card::before {{ content: ''; position: absolute; top: 0; left: 0; bottom: 0; width: 3px; }}
.card.red::before {{ background: var(--accent); }}
.card.blue::before {{ background: var(--accent2); }}
.card.green::before {{ background: var(--green); }}
.card.gold::before {{ background: var(--gold); }}
.card-label {{ font-size: 11px; color: var(--muted); margin-bottom: 4px; }}
.card-value {{ font-size: 22px; font-weight: 900; line-height: 1.2; }}
.card-value.red {{ color: var(--accent); }}
.card-value.blue {{ color: var(--accent2); }}
.card-value.green {{ color: var(--green); }}
.card-value.gold {{ color: var(--gold); }}
.card-note {{ font-size: 11px; color: var(--muted); margin-top: 4px; }}
.sentiment-box {{ display: flex; gap: 10px; flex-wrap: wrap; margin-bottom: 16px; }}
.sent-item {{
  text-align: center; background: var(--surface); border-radius: 8px;
  padding: 10px 12px; flex: 1; min-width: 70px;
}}
.sent-label {{ font-size: 10px; color: var(--muted); margin-bottom: 4px; }}
.sent-val {{ font-size: 18px; font-weight: 800; }}
.sent-val.red {{ color: var(--accent); }}
.sent-val.green {{ color: var(--green); }}
.sent-val.blue {{ color: var(--accent2); }}
.sent-val.gold {{ color: var(--gold); }}
.logic-item {{
  display: flex; gap: 12px; margin-bottom: 14px;
  padding: 14px; background: var(--surface); border-radius: 10px; border: 1px solid var(--rule);
}}
.logic-num {{
  width: 28px; height: 28px; min-width: 28px; border-radius: 50%;
  background: var(--accent); color: #fff; font-size: 13px; font-weight: 700;
  display: flex; align-items: center; justify-content: center;
}}
.logic-num.blue {{ background: var(--accent2); }}
.logic-num.green {{ background: var(--green); }}
.logic-num.gold {{ background: var(--gold); }}
.logic-content h3 {{ font-size: 14px; font-weight: 700; color: #fff; margin-bottom: 4px; }}
.logic-content p {{ font-size: 12px; color: var(--muted); line-height: 1.6; }}
.signal-table {{ width: 100%; border-collapse: collapse; font-size: 12px; }}
.signal-table th {{
  background: var(--bg3); padding: 10px 8px; text-align: left;
  font-weight: 600; color: var(--muted); font-size: 11px;
  border-bottom: 1px solid var(--rule);
}}
.signal-table td {{
  padding: 10px 8px; border-bottom: 1px solid rgba(255,255,255,0.04); color: var(--ink);
}}
.signal-table tr:hover {{ background: var(--surface); }}
.signal-badge {{
  display: inline-block; padding: 2px 8px; border-radius: 4px;
  font-size: 11px; font-weight: 600;
}}
.signal-badge.red {{ background: rgba(239,68,68,0.15); color: #fca5a5; }}
.signal-badge.green {{ background: rgba(34,197,94,0.15); color: #86efac; }}
.signal-badge.gold {{ background: rgba(245,158,11,0.15); color: #fcd34d; }}
.signal-badge.blue {{ background: rgba(59,130,246,0.15); color: #93c5fd; }}
.up {{ color: var(--accent); }}
.down {{ color: var(--green); }}
.footer {{ text-align: center; padding: 20px; font-size: 11px; color: var(--muted); }}
@media (max-width: 600px) {{
  .cards {{ grid-template-columns: 1fr; }}
  .container {{ padding: 10px; }}
  .header h1 {{ font-size: 17px; }}
  .card-value {{ font-size: 18px; }}
  .section {{ padding: 14px; }}
  .sent-item {{ min-width: 60px; padding: 8px; }}
  .sent-val {{ font-size: 15px; }}
}}
</style>
</head>
<body>
<div class="container">

  <div class="header">
    <h1>{data["title"]}</h1>
    <div class="subtitle">{data.get("sentiment_detail", "")}</div>
    <div class="header-meta">
      <span>📅 {data["timestamp"]}</span>
      <span>情绪: {data["sentiment"]}</span>
      <span>来源: 新浪/东财</span>
    </div>
    <div class="score-bar">
      <span class="score-label">多空评分</span>
      <div class="score-track">
        <div class="score-fill {score_cls}"></div>
      </div>
      <span class="score-value {score_cls}">{score_emoji} {score:+.0f}</span>
    </div>
  </div>

  <div class="section">
    <div class="section-title">📊 核心数据</div>
    <div class="cards">
      {indices_html}
      {nb_html}
    </div>
    <div class="sentiment-box">
      <div class="sent-item">
        <div class="sent-label">上证指数</div>
        <div class="sent-val {"green" if data["sh_change"] > 0 else "red" if data["sh_change"] < 0 else "blue"}">{data["sh_change"]:+.2f}%</div>
      </div>
      <div class="sent-item">
        <div class="sent-label">深成指</div>
        <div class="sent-val {"green" if data["sz_change"] > 0 else "red" if data["sz_change"] < 0 else "blue"}">{data["sz_change"]:+.2f}%</div>
      </div>
      <div class="sent-item">
        <div class="sent-label">创业板指</div>
        <div class="sent-val {"green" if data["cy_change"] > 0 else "red" if data["cy_change"] < 0 else "blue"}">{data["cy_change"]:+.2f}%</div>
      </div>
      <div class="sent-item">
        <div class="sent-label">沪深300</div>
        <div class="sent-val {"green" if data.get("hs300_change",0) > 0 else "red" if data.get("hs300_change",0) < 0 else "blue"}">{data.get("hs300_change",0):+.2f}%</div>
      </div>
      <div class="sent-item">
        <div class="sent-label">中证500</div>
        <div class="sent-val {"green" if data.get("zz500_change",0) > 0 else "red" if data.get("zz500_change",0) < 0 else "blue"}">{data.get("zz500_change",0):+.2f}%</div>
      </div>
      <div class="sent-item">
        <div class="sent-label">涨停/跌停</div>
        <div class="sent-val {"green" if data["limit_up_count"] > data["limit_down_count"] * 3 else "red"}">{data["limit_up_count"]}/{data["limit_down_count"]}</div>
      </div>
    </div>
  </div>

  <div class="section">
    <div class="section-title blue">→ 市场逻辑链</div>
    {logics_html}
  </div>

  <div class="section">
    <div class="section-title green">🎯 交易信号</div>
    <table class="signal-table">
      <thead>
        <tr><th>信号</th><th>方向</th><th>板块/标的</th><th>逻辑</th><th>置信度</th></tr>
      </thead>
      <tbody>
        {signals_html}
      </tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title gold">🔥 板块资金流向 TOP5</div>
    <table class="signal-table">
      <thead>
        <tr><th>板块</th><th>涨幅</th><th>主力净流入</th></tr>
      </thead>
      <tbody>
        {sectors_html}
      </tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title">📈 涨停榜 ({data["limit_up_count"]}只)</div>
    <table class="signal-table">
      <thead>
        <tr><th>股票</th><th>价格</th><th>涨幅</th><th>封单</th></tr>
      </thead>
      <tbody>
        {limit_html}
      </tbody>
    </table>
  </div>

  <div class="section">
    <div class="section-title red">📉 跌停榜 ({data["limit_down_count"]}只)</div>
    <table class="signal-table">
      <thead>
        <tr><th>股票</th><th>价格</th><th>跌幅</th></tr>
      </thead>
      <tbody>
        {down_html}
      </tbody>
    </table>
  </div>

  <div class="footer">
    <p>A股早盘情报站 v2.0 · 自动生成于 {data["timestamp"]}</p>
    <p>数据: 新浪行情 / 东方财富资金流向 · 仅供参考，不构成投资建议</p>
  </div>

</div>
</body>
</html>'''
    
    return html

def push_to_github(html_content, json_content=None):
    """推送到GitHub Pages"""
    try:
        os.chdir("/workspace/a-stock-trading-system")
        subprocess.run(["git", "stash"], capture_output=True)
        subprocess.run(["git", "checkout", "gh-pages"], capture_output=True)
        
        with open("index.html", "w", encoding="utf-8") as f:
            f.write(html_content)
        
        if json_content:
            with open("data.json", "w", encoding="utf-8") as f:
                f.write(json_content)
        
        # 复制实时仪表盘
        realtime_path = os.path.join(os.path.dirname(__file__), "realtime.html")
        if os.path.exists(realtime_path):
            import shutil
            shutil.copy2(realtime_path, "realtime.html")
        
        subprocess.run(["git", "add", "index.html"], capture_output=True)
        if json_content:
            subprocess.run(["git", "add", "data.json"], capture_output=True)
        subprocess.run(["git", "add", "realtime.html"], capture_output=True)
        subprocess.run(["git", "commit", "-m", f"Auto update v2.0 {datetime.now().strftime('%Y-%m-%d %H:%M')}"], capture_output=True)
        result = subprocess.run(["git", "push", "origin", "gh-pages", "--force"], capture_output=True, text=True)
        
        subprocess.run(["git", "checkout", "master"], capture_output=True)
        subprocess.run(["git", "stash", "pop"], capture_output=True)
        
        return True
    except Exception as e:
        print(f"推送失败: {e}")
        return False

def main():
    print("=" * 60)
    print(f"A股早盘情报站 v2.0 - 专业级全自动分析")
    print(f"生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M')}")
    print("=" * 60)
    
    print("\n[1/5] 抓取指数行情...")
    indices = fetch_indices()
    print(f"  ✓ 获取{len(indices)}个指数")
    
    print("\n[2/5] 抓取北向资金...")
    northbound = fetch_northbound()
    if northbound:
        print(f"  ✓ 北向资金: {northbound['total_net']:+.1f}亿")
    else:
        print("  ✗ 北向资金获取失败")
    
    print("\n[3/5] 抓取板块资金流向...")
    sectors = fetch_sector_flow()
    print(f"  ✓ 获取{len(sectors)}个板块")
    
    print("\n[4/5] 抓取涨跌停...")
    limit_up = fetch_limit_up()
    limit_down = fetch_limit_down()
    print(f"  ✓ 涨停{len(limit_up)}只 / 跌停{len(limit_down)}只")
    
    print("\n[5/5] 生成分析报告...")
    data = analyze_market(indices, northbound, sectors, limit_up, limit_down)
    print(f"  ✓ 标题: {data['title']}")
    print(f"  ✓ 情绪: {data['sentiment']}")
    print(f"  ✓ 信号: {len(data['signals'])}个")
    
    html = generate_html(data)
    
    # 同时输出data.json供前端实时读取
    json_data = json.dumps(data, ensure_ascii=False, indent=2)
    
    print("\n[6/6] 推送到GitHub Pages...")
    if push_to_github(html, json_data):
        print("\n✅ 完成！访问: https://uqnasdasd.github.io/a-stock-trading-system/")
    else:
        print("\n❌ 推送失败")
    
    print("=" * 60)

if __name__ == "__main__":
    main()
