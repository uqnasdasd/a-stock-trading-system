"""抓取A股实时数据并保存到GitHub仓库"""
import json
import urllib.request
from datetime import datetime

def fetch_indices():
    """获取指数行情"""
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
            indices.append({"code": code, "name": codes.get(code, code), "price": cur, "change_pct": round((cur - pre) / pre * 100, 2) if pre else 0})
        return indices
    except Exception as e:
        print(f"indices error: {e}")
        return []

def fetch_limit_up():
    """获取涨停股票"""
    try:
        url = f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=30&sort=fbt%3Aasc&date={datetime.now().strftime('%Y%m%d')}"
        req = urllib.request.Request(url, headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [{"code": i.get("c",""), "name": i.get("n",""), "price": i.get("p",0), "change_pct": i.get("zdp",0)} for i in data.get("data",{}).get("pool",[])]
    except Exception as e:
        print(f"limit error: {e}")
        return []

def fetch_limit_down():
    """获取跌停股票"""
    try:
        url = f"https://push2ex.eastmoney.com/getTopicZTPool?ut=7eea3edcaed734bea9cbfc24409ed989&dpt=wz.ztzt&Pageindex=0&pagesize=30&sort=fbt%3Aasc&date={datetime.now().strftime('%Y%m%d')}"
        req = urllib.request.Request(url.replace("ztzt", "ztdt"), headers={"User-Agent": "Mozilla/5.0"})
        with urllib.request.urlopen(req, timeout=10) as resp:
            data = json.loads(resp.read().decode("utf-8"))
        return [{"code": i.get("c",""), "name": i.get("n",""), "price": i.get("p",0), "change_pct": i.get("zdp",0)} for i in data.get("data",{}).get("pool",[])]
    except Exception as e:
        print(f"limit_down error: {e}")
        return []

def main():
    now = datetime.now()

    indices = fetch_indices()
    limit_up = fetch_limit_up()
    limit_down = fetch_limit_down()

    up_count = sum(1 for i in indices if i["change_pct"] > 0)
    down_count = sum(1 for i in indices if i["change_pct"] < 0)
    score = round(up_count / max(up_count + down_count, 1) * 100)

    result = {
        "timestamp": now.strftime("%Y-%m-%d %H:%M:%S"),
        "indices": indices,
        "sentiment": {"score": score, "up": up_count, "down": down_count, "limit_up": len(limit_up), "limit_down": len(limit_down)},
        "limit_up": limit_up[:30],
        "limit_down": limit_down[:30],
    }

    # 保存到data目录
    with open("data/market.json", "w", encoding="utf-8") as f:
        json.dump(result, f, ensure_ascii=False, indent=2)

    print(f"数据更新成功: {now.strftime('%H:%M:%S')} 指数{len(indices)} 涨停{len(limit_up)} 跌停{len(limit_down)}")

if __name__ == "__main__":
    main()
