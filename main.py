import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 戰區板塊定義
SECTORS = {
    "AI 新貴": ["0100.HK", "2513.HK", "3317.HK"],
    "科技龍頭": ["1810.HK", "3690.HK", "0700.HK", "9988.HK"],
    "汽車與鋰電": ["1211.HK", "1772.HK", "2015.HK"],
    "電力與能源": ["3393.HK", "2208.HK", "0916.HK"],
    "黃金避險": ["2840.HK", "GC=F"]
}

def get_aastock_flow(symbol):
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        # 抓取資金流向與成交量
        flow = soup.find(id="cp_objQuote_lblCapitalInflow").text
        vol = soup.find(id="cp_objQuote_lblVolume").text
        return flow.strip(), vol.strip()
    except: return "數據傳輸中", "N/A"

def get_lego_sequence(df):
    sequence = []
    close = df['Close'].squeeze()
    high = df['High'].squeeze()
    low = df['Low'].squeeze()
    for i in range(-5, 0):
        try:
            curr = close.iloc[i]
            prev_5d_high = high.iloc[i-5:i].max()
            prev_5d_low = low.iloc[i-5:i].min()
            if curr > prev_5d_high: sequence.append("red")
            elif curr < prev_5d_low: sequence.append("blue")
            else: sequence.append("gray")
        except: sequence.append("gray")
    return sequence

def get_pattern(df):
    c, h, l, o = df['Close'].squeeze(), df['High'].squeeze(), df['Low'].squeeze(), df['Open'].squeeze()
    ma5 = c.rolling(5).mean()
    # ✈️ 飛機：均線多頭且角度向上
    if c.iloc[-1] > ma5.iloc[-1] and ma5.iloc[-1] > ma5.iloc[-2]: return "✈️ 飛機起飛"
    # 🦴 骨頭：上影線極長 (洗盤)
    upper_shadow = h.iloc[-1] - max(c.iloc[-1], o.iloc[-1])
    if upper_shadow > abs(c.iloc[-1] - o.iloc[-1]) * 1.5: return "🦴 骨頭洗盤"
    # 👑 皇冠：創 20 日新高
    if c.iloc[-1] >= h.tail(20).max(): return "👑 皇冠突破"
    return "觀察中"

def main():
    final_results = {}
    now = datetime.now().strftime("%Y-%m-%d %H:%M")
    
    for sector, members in SECTORS.items():
        sector_data = []
        for s in members:
            try:
                df = yf.download(s, period="40d", interval="1d", progress=False)
                if df.empty: continue
                
                flow, vol_real = get_aastock_flow(s)
                res = {
                    "symbol": s,
                    "price": round(float(df['Close'].iloc[-1]), 3),
                    "lego": get_lego_sequence(df),
                    "pattern": get_pattern(df),
                    "flow": flow,
                    "vol": vol_real,
                    "change": f"{round(df['Close'].pct_change().iloc[-1]*100, 2)}%"
                }
                sector_data.append(res)
                time.sleep(0.5)
            except: continue
        final_results[sector] = sector_data

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump({"update": now, "sectors": final_results}, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
