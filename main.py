import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 修正後的標的及其板塊同業 (100: MINIMAX, 2513: 智譜, 3317: 迅策)
STOCKS_MAP = {
    "1810.HK": ["0700.HK", "9988.HK", "3690.HK"],
    "1211.HK": ["2015.HK", "9868.HK", "9866.HK"],
    "0100.HK": ["2513.HK", "3317.HK"], # AI 板塊：MINIMAX 帶領 智譜與迅策
    "3690.HK": ["9988.HK", "0700.HK", "1024.HK"],
    "1772.HK": ["300750.SZ", "002460.SZ"],
    "3393.HK": ["1088.HK", "0902.HK", "0038.HK"],
    "2208.HK": ["0958.HK", "0916.HK", "1798.HK"],
    "2840.HK": ["GC=F", "PAXG-USD"]
}

def get_aastock_flow(symbol):
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        flow = soup.find(id="cp_objQuote_lblCapitalInflow")
        return flow.text.strip() if flow else "流向計算中"
    except: return "連線超時"

def pro_analysis(df):
    try:
        c, v, h, l, o = df['Close'].squeeze(), df['Volume'].squeeze(), df['High'].squeeze(), df['Low'].squeeze(), df['Open'].squeeze()
        
        # 張士佳 LEGO 邏輯
        lego = "整理"
        if c.iloc[-1] > h.iloc[-6:-1].max() and v.iloc[-1] > v.tail(10).mean(): lego = "強勢紅磚"
        elif c.iloc[-1] < l.iloc[-6:-1].min(): lego = "弱勢藍磚"

        # 形態識別
        pattern = "觀察中"
        ma5, ma20 = c.rolling(5).mean(), c.rolling(20).mean()
        
        # 飛機起飛 (均線多頭)
        if c.iloc[-1] > ma5.iloc[-1] > ma20.iloc[-1] and (ma5.iloc[-1] > ma5.iloc[-2]): pattern = "✈️ 飛機起飛"
        # 咖啡杯柄
        elif c.iloc[-1] > c.iloc[-20] * 0.98 and v.iloc[-1] < v.tail(5).mean(): pattern = "☕ 咖啡杯柄"
        # 骨頭形態 (洗盤判定：長上影線且縮量)
        upper_shadow = h.iloc[-1] - max(c.iloc[-1], o.iloc[-1])
        body = abs(c.iloc[-1] - o.iloc[-1])
        if upper_shadow > (body * 2) and v.iloc[-1] < v.tail(5).mean(): pattern = "🦴 骨頭洗盤"
        # 皇冠突破
        if c.iloc[-1] >= h.tail(60).max() * 0.99: pattern = "👑 皇冠突破"

        return {
            "price": round(float(c.iloc[-1]), 3) if c.iloc[-1] < 1 else round(float(c.iloc[-1]), 2),
            "lego": lego, "pattern": pattern,
            "volume": f"{int(v.iloc[-1]/10000)}萬", "raw_change": float(c.pct_change().iloc[-1])
        }
    except: return None

def main():
    final_results = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    for main_stock, peers in STOCKS_MAP.items():
        try:
            df = yf.download(main_stock, period="90d", interval="1d", progress=False)
            if df.empty: continue
            res = pro_analysis(df)
            if not res: continue
            
            peer_changes = []
            for p in peers:
                p_df = yf.download(p, period="5d", interval="1d", progress=False)
                if not p_df.empty: peer_changes.append(p_df['Close'].pct_change().iloc[-1])
            
            avg_peer = np.mean(peer_changes) if peer_changes else 0
            res['sector_strength'] = "強於同業" if res['raw_change'] > avg_peer else "弱於同業"
            res['flow'] = get_aastock_flow(main_stock)
            res['update'] = current_time
            
            # 加上中文名稱標註 (針對 AI 標的)
            names = {"0100.HK": "MINIMAX", "2513.HK": "智譜 AI", "3317.HK": "迅策科技"}
            res['name'] = names.get(main_stock, "")
            
            final_results[main_stock] = res
            time.sleep(0.5)
        except: continue
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
