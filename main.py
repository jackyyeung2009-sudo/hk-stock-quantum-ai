import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 標的與板塊同業地圖
STOCKS_MAP = {
    "0100.HK": ["2513.HK", "3317.HK", "0700.HK"], # AI 板塊 (MINIMAX/智譜/迅策)
    "1810.HK": ["0700.HK", "9988.HK", "3690.HK"], # 科技板塊
    "1211.HK": ["2015.HK", "9868.HK", "9866.HK"], # 汽車板塊
    "3690.HK": ["9988.HK", "0700.HK", "1024.HK"], # 消費/外賣
    "1772.HK": ["300750.SZ", "002460.SZ"],        # 鋰電
    "3393.HK": ["1088.HK", "0902.HK", "0038.HK"], # 電力
    "2208.HK": ["0958.HK", "0916.HK", "1798.HK"], # 風電
    "2840.HK": ["GC=F", "PAXG-USD"]               # 黃金
}

def get_aastock_flow(symbol):
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        flow = soup.find(id="cp_objQuote_lblCapitalInflow").text
        return flow.strip()
    except: return "流向計算中"

def get_lego_sequence(df):
    """生成過去 5 日的 LEGO 顏色序列"""
    sequence = []
    # 確保有足夠數據計算 5 日突破
    for i in range(-5, 0):
        try:
            current_close = df['Close'].iloc[i]
            # 參考過去 5 日的高低點
            window = df.iloc[i-5:i]
            prev_high = window['High'].max()
            prev_low = window['Low'].min()
            
            if current_close > prev_high: sequence.append("red")
            elif current_close < prev_low: sequence.append("blue")
            else: sequence.append("gray")
        except: sequence.append("gray")
    return sequence

def pro_analysis(df):
    c, v, h, l, o = df['Close'].squeeze(), df['Volume'].squeeze(), df['High'].squeeze(), df['Low'].squeeze(), df['Open'].squeeze()
    ma5, ma20 = c.rolling(5).mean(), c.rolling(20).mean()
    
    pattern = "觀察中"
    if c.iloc[-1] > ma5.iloc[-1] > ma20.iloc[-1]: pattern = "✈️ 飛機起飛"
    elif (h.iloc[-1] - max(c.iloc[-1], o.iloc[-1])) > (abs(c.iloc[-1]-o.iloc[-1])*2): pattern = "🦴 骨頭洗盤"
    elif c.iloc[-1] >= h.tail(60).max() * 0.99: pattern = "👑 皇冠突破"
    
    return {
        "price": round(float(c.iloc[-1]), 3) if c.iloc[-1] < 2 else round(float(c.iloc[-1]), 2),
        "lego_seq": get_lego_sequence(df),
        "pattern": pattern,
        "vol": f"{int(v.iloc[-1]/10000)}萬",
        "raw_change": float(c.pct_change().iloc[-1])
    }

def main():
    final_results = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    names = {"0100.HK": "MINIMAX (100)", "2513.HK": "智譜 (2513)", "3317.HK": "迅策 (3317)"}

    for main_stock, peers in STOCKS_MAP.items():
        try:
            df = yf.download(main_stock, period="60d", interval="1d", progress=False)
            if df.empty: continue
            
            res = pro_analysis(df)
            res['flow'] = get_aastock_flow(main_stock)
            
            # 計算板塊強度 (Peer Avg)
            peer_changes = []
            for p in peers:
                p_df = yf.download(p, period="2d", interval="1d", progress=False)
                if not p_df.empty: peer_changes.append(p_df['Close'].pct_change().iloc[-1])
            
            avg_peer = np.mean(peer_changes) if peer_changes else 0
            res['sector_strength'] = "強於板塊" if res['raw_change'] > avg_peer else "板塊跟隨"
            res['name'] = names.get(main_stock, "")
            res['update'] = current_time
            final_results[main_stock] = res
            time.sleep(0.5)
        except: continue
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
