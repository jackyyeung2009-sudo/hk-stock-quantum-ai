import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 戰區板塊定義：精確對齊你的要求
SECTORS = {
    "AI 新貴": ["0100.HK", "2513.HK", "3317.HK"],
    "科技與平台": ["1810.HK", "3690.HK", "0700.HK", "9988.HK"],
    "汽車與鋰電": ["1211.HK", "1772.HK", "2015.HK"],
    "新能源與電力": ["3393.HK", "2208.HK", "0958.HK"],
    "商品避險": ["2840.HK", "GC=F"]
}

def get_aastock_data(symbol):
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        flow = soup.find(id="cp_objQuote_lblCapitalInflow").text
        vol = soup.find(id="cp_objQuote_lblVolume").text
        return flow.strip(), vol.strip()
    except: return "流向計算中", "N/A"

def analyze_stock(df):
    try:
        c, h, l, o, v = df['Close'].squeeze(), df['High'].squeeze(), df['Low'].squeeze(), df['Open'].squeeze(), df['Volume'].squeeze()
        
        # 1. 張士佳 LEGO 5D 序列
        lego_seq = []
        for i in range(-5, 0):
            window = df.iloc[i-5:i]
            if c.iloc[i] > window['High'].max(): lego_seq.append("red")
            elif c.iloc[i] < window['Low'].min(): lego_seq.append("blue")
            else: lego_seq.append("gray")
            
        # 2. 命中率 70% 形態邏輯
        pattern = "觀察中"
        ma5, ma10, ma20 = c.rolling(5).mean(), c.rolling(10).mean(), c.rolling(20).mean()
        
        # 飛機起飛 (Airplane): 均線金叉且向上
        if c.iloc[-1] > ma5.iloc[-1] > ma10.iloc[-1] and ma5.iloc[-1] > ma5.iloc[-2]:
            pattern = "✈️ 飛機起飛"
        # 骨頭形態 (Bone): 長上影線且縮量 (洗盤信號)
        elif (h.iloc[-1] - max(c.iloc[-1], o.iloc[-1])) > abs(c.iloc[-1]-o.iloc[-1])*1.5:
            pattern = "🦴 骨頭洗盤"
        # 皇冠形態 (Crown): 20日新高突破
        elif c.iloc[-1] >= h.tail(20).max() * 0.99:
            pattern = "👑 皇冠突破"
        # 咖啡杯 (Cup): 縮量盤整回升
        elif c.iloc[-1] > c.iloc[-10] and v.iloc[-1] < v.tail(5).mean():
            pattern = "☕ 咖啡杯柄"

        return {
            "price": round(float(c.iloc[-1]), 3) if c.iloc[-1] < 2 else round(float(c.iloc[-1]), 2),
            "lego": lego_seq,
            "pattern": pattern,
            "change": f"{round(c.pct_change().iloc[-1]*100, 2)}%"
        }
    except: return None

def main():
    final_output = {}
    now_str = datetime.now().strftime("%Y-%m-%d %H:%M")
    names = {"0100.HK": "MINIMAX", "2513.HK": "智譜 AI", "3317.HK": "迅策科技"}

    for sector, stocks in SECTORS.items():
        sector_results = []
        for s in stocks:
            try:
                df = yf.download(s, period="40d", interval="1d", progress=False)
                if df.empty: continue
                
                analysis = analyze_stock(df)
                if not analysis: continue
                
                flow, vol_real = get_aastock_flow(s) if ".HK" in s else ("N/A", "N/A")
                analysis.update({
                    "symbol": s,
                    "name": names.get(s, ""),
                    "flow": flow,
                    "vol": vol_real
                })
                sector_results.append(analysis)
                time.sleep(0.5)
            except: continue
        final_output[sector] = sector_results

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump({"update": now_str, "sectors": final_output}, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
