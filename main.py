import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 規則：標的及其板塊同業
STOCKS_MAP = {
    "0100.HK": ["2513.HK", "3317.HK", "0700.HK"], # AI 新貴板塊
    "1810.HK": ["0700.HK", "9988.HK", "3690.HK"], # 科技板塊
    "1211.HK": ["2015.HK", "9868.HK", "9866.HK"], # 汽車板塊
    "3690.HK": ["9988.HK", "0700.HK", "1024.HK"], # 消費/外賣
    "1772.HK": ["300750.SZ", "002460.SZ"],        # 鋰電
    "3393.HK": ["1088.HK", "0902.HK"],           # 電力
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
    except: return "N/A"

def get_lego_blocks(df):
    """計算過去 5 日的 LEGO 顏色序列"""
    blocks = []
    c, h, l, v = df['Close'], df['High'], df['Low'], df['Volume']
    for i in range(-5, 0):
        prev_h = h.iloc[i-5:i].max()
        prev_l = l.iloc[i-5:i].min()
        if c.iloc[i] > prev_h: blocks.append("red")
        elif c.iloc[i] < prev_l: blocks.append("blue")
        else: blocks.append("gray")
    return blocks

def pro_analysis(df):
    c, v, h, l, o = df['Close'].squeeze(), df['Volume'].squeeze(), df['High'].squeeze(), df['Low'].squeeze(), df['Open'].squeeze()
    ma5, ma20 = c.rolling(5).mean(), c.rolling(20).mean()
    
    pattern = "觀察中"
    if c.iloc[-1] > ma5.iloc[-1] > ma20.iloc[-1]: pattern = "✈️ 飛機起飛"
    elif (h.iloc[-1] - max(c.iloc[-1], o.iloc[-1])) > (abs(c.iloc[-1]-o.iloc[-1])*2): pattern = "🦴 骨頭洗盤"
    
    return {
        "price": round(float(c.iloc[-1]), 3),
        "lego_history": get_lego_blocks(df),
        "pattern": pattern,
        "vol": f"{int(v.iloc[-1]/10000)}萬",
        "change": float(c.pct_change().iloc[-1])
    }

def main():
    final_results = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    names = {"0100.HK": "MINIMAX", "2513.HK": "智譜 AI", "3317.HK": "迅策科技"}

    for main_stock, peers in STOCKS_MAP.items():
        try:
            df = yf.download(main_stock, period="60d", interval="1d", progress=False)
            if df.empty: continue
            
            res = pro_analysis(df)
            res['flow'] = get_aastock_flow(main_stock)
            
            # 板塊算力：計算同業平均漲幅與總流量
            peer_changes = []
            for p in peers:
                p_df = yf.download(p, period="2d", interval="1d", progress=False)
                if not p_df.empty: peer_changes.append(p_df['Close'].pct_change().iloc[-1])
            
            res['sector_flow'] = "流入" if np.mean(peer_changes) > 0 else "流出"
            res['name'] = names.get(main_stock, "")
            res['update'] = current_time
            final_results[main_stock] = res
            time.sleep(0.5)
        except: continue
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
