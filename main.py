import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
from datetime import datetime
import time

# 標的清單 (排除無效代碼，確保零幻覺)
STOCKS = ["1810.HK", "1211.HK", "3690.HK", "2840.HK", "2208.HK", "1772.HK", "3393.HK", "0100.HK", "2513.HK", "3317.HK"]

def get_aastock_flow(symbol):
    """最高算力抓取 AAStock 實時資金流 (加強模擬瀏覽器)"""
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
        'Accept-Language': 'zh-HK,zh;q=0.9,en;q=0.8'
    }
    try:
        # 加入延時防止被封
        time.sleep(1) 
        r = requests.get(url, headers=headers, timeout=15)
        soup = BeautifulSoup(r.text, 'lxml')
        flow_tag = soup.find(id="cp_objQuote_lblCapitalInflow")
        return flow_tag.text.strip() if flow_tag else "無數據"
    except Exception as e:
        return f"連線超時"

def analyze_logic(df):
    """技術分析：LEGO + 複合形態"""
    try:
        c = df['Close']
        v = df['Volume']
        h = df['High']
        l = df['Low']
        
        # 張士佳 LEGO 邏輯
        is_lego = "整理"
        if c.iloc[-1] > h.iloc[-6:-1].max() and v.iloc[-1] > v.tail(10).mean():
            is_lego = "強勢紅磚"
        elif c.iloc[-1] < l.iloc[-6:-1].min():
            is_lego = "弱勢藍磚"

        # 形態識別
        pattern = "觀察中"
        ma5 = c.rolling(5).mean()
        ma20 = c.rolling(20).mean()
        
        if c.iloc[-1] > ma5.iloc[-1] > ma20.iloc[-1] and (ma5.iloc[-1] > ma5.iloc[-2]):
            pattern = "✈️ 飛機起飛"
        elif c.iloc[-1] > c.iloc[-20] * 0.98 and v.iloc[-1] < v.tail(5).mean():
            pattern = "☕ 咖啡杯形態"
        elif (h.iloc[-1] - c.iloc[-1]) / (h.iloc[-1] - l.iloc[-1] + 0.0001) > 0.6:
            pattern = "🦴 骨頭回測"

        return {
            "price": round(float(c.iloc[-1]), 2),
            "lego": is_lego,
            "pattern": pattern,
            "volume": f"{int(v.iloc[-1]/10000)}萬"
        }
    except:
        return {"price": 0, "lego": "計算錯誤", "pattern": "數據缺失", "volume": "0"}

def main():
    results = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for s in STOCKS:
        print(f"正在分析 {s}...")
        try:
            # 抓取 YFinance
            df = yf.download(s, period="60d", interval="1d", progress=False)
            if df.empty:
                continue
                
            analysis = analyze_logic(df)
            flow = get_aastock_flow(s)
            
            results[s] = {**analysis, "flow": flow, "update": current_time}
        except Exception as e:
            print(f"跳過 {s}，原因: {e}")

    # 確保寫入 JSON
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(results, f, ensure_ascii=False, indent=4)
    print("✅ 數據已成功寫入 data.json")

if __name__ == "__main__":
    main()
