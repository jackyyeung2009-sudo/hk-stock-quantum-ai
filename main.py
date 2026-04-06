import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 戰區板塊定義 - 嚴格遵守 Jack 的清單
SECTORS_MAP = {
    "AI 新貴 (100/2513/3317)": ["0100.HK", "2513.HK", "3317.HK"],
    "科技龍頭與平台": ["1810.HK", "3690.HK", "0700.HK", "9988.HK"],
    "汽車與鋰電板塊": ["1211.HK", "1772.HK", "2015.HK"],
    "新能源與電力": ["3393.HK", "2208.HK", "0958.HK"],
    "黃金與商品避險": ["2840.HK", "GC=F"]
}

def get_aastock_flow(symbol):
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        flow = soup.find(id="cp_objQuote_lblCapitalInflow").text
        vol = soup.find(id="cp_objQuote_lblVolume").text
        return flow.strip(), vol.strip()
    except: return "流向計算中", "N/A"

def analyze_logic(df):
    try:
        # 【核心修正】徹底解決 yfinance 2026 多重索引導致的數據抓取失敗
        if isinstance(df.columns, pd.MultiIndex):
            df.columns = df.columns.get_level_values(0)
        
        c = df['Close'].ffill()
        h = df['High'].ffill()
        l = df['Low'].ffill()
        o = df['Open'].ffill()
        v = df['Volume'].ffill()

        # LEGO 5D 序列 (對比過去5日高低)
        lego = []
        for i in range(-5, 0):
            prev_5d = df.iloc[i-5:i]
            if c.iloc[i] > prev_5d['High'].max(): lego.append("red")
            elif c.iloc[i] < prev_5d['Low'].min(): lego.append("blue")
            else: lego.append("gray")

        # 命中率 70% 形態推斷
        pattern = "觀察中"
        ma5 = c.rolling(5).mean()
        # ✈️ 飛機: 股價在5日線上且5日線轉強
        if c.iloc[-1] > ma5.iloc[-1] and ma5.iloc[-1] > ma5.iloc[-2]: pattern = "✈️ 飛機起飛"
        # 🦴 骨頭: 上影線長度 > 實體 1.5 倍
        elif (h.iloc[-1] - max(c.iloc[-1], o.iloc[-1])) > abs(c.iloc[-1]-o.iloc[-1])*1.5: pattern = "🦴 骨頭洗盤"
        # 👑 皇冠: 突破20日新高
        elif c.iloc[-1] >= h.tail(20).max() * 0.99: pattern = "👑 皇冠突破"

        return {
            "price": round(float(c.iloc[-1]), 3),
            "lego": lego,
            "pattern": pattern,
            "change": f"{round(c.pct_change().iloc[-1]*100, 2)}%"
        }
    except: return None

def main():
    final_data = []
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    names = {"0100.HK": "MINIMAX", "2513.HK": "智譜 AI", "3317.HK": "迅策科技"}

    for sector, stocks in SECTORS_MAP.items():
        for s in stocks:
            try:
                df = yf.download(s, period="40d", interval="1d", progress=False)
                analysis = analyze_logic(df)
                if analysis:
                    flow, vol = get_aastock_flow(s) if ".HK" in s else ("N/A", "N/A")
                    # 採用扁平化結構，防止前端讀取失敗
                    final_data.append({
                        "sector": sector, "symbol": s, "name": names.get(s, ""),
                        "flow": flow, "vol": vol, **analysis, "update": now
                    })
                time.sleep(0.5)
            except: continue

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)
    print(f"✅ V11.0 算力同步完成，數據點位：{len(final_data)}")

if __name__ == "__main__":
    main()
