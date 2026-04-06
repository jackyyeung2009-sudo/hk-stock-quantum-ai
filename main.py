import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 標的及其板塊同業 (1810->科技, 0100->AI, 1211->汽車, 1772->鋰電, 3393->電力設備)
STOCKS_MAP = {
    "1810.HK": ["0700.HK", "9988.HK", "3690.HK"], # 科技龍頭
    "0100.HK": ["2513.HK", "3317.HK"],            # AI科技
    "1211.HK": ["2015.HK", "9868.HK", "9866.HK"], # 電車三傻
    "1772.HK": ["300750.SZ", "002460.SZ"],        # 鋰電龍頭 (A股聯動)
    "3393.HK": ["1088.HK", "0902.HK"],           # 電力/基建
    "2840.HK": ["XAUUSD=X"]                       # 金價連動
}

def get_aastock_flow(symbol):
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        flow = soup.find(id="cp_objQuote_lblCapitalInflow").text
        return flow
    except: return "N/A"

def pro_analysis(df, symbol):
    """最高算力形態識別公式"""
    c = df['Close']
    v = df['Volume']
    h = df['High']
    l = df['Low']
    
    # 1. 飛機起飛 (Slope Analysis)
    ma5 = c.rolling(5).mean()
    ma10 = c.rolling(10).mean()
    slope = (ma5.iloc[-1] - ma5.iloc[-3]) / ma5.iloc[-3] * 100
    is_plane = slope > 2 and c.iloc[-1] > ma5.iloc[-1] > ma10.iloc[-1]
    
    # 2. 咖啡杯 (Cup and Handle)
    # 尋找過去30天是否有圓弧底，且目前處於縮量回踩
    min_idx = c.tail(30).idxmin()
    is_cup = c.iloc[-1] > c.tail(30).mean() and v.iloc[-1] < v.tail(5).mean()
    
    # 3. 皇冠與骨頭 (Shadow analysis)
    upper_shadow = (h.iloc[-1] - max(c.iloc[-1], df['Open'].iloc[-1]))
    body = abs(c.iloc[-1] - df['Open'].iloc[-1])
    is_bone = upper_shadow > body * 2 # 骨頭：長上影線
    
    # LEGO 判定
    lego = "整理"
    if c.iloc[-1] > h.iloc[-6:-1].max() and v.iloc[-1] > v.tail(10).mean():
        lego = "強勢紅磚"
    
    pattern = "觀察"
    if is_plane: pattern = "✈️ 飛機起飛"
    elif is_cup: pattern = "☕ 咖啡杯柄"
    elif is_bone: pattern = "🦴 骨頭洗盤"
    
    return {"price": round(float(c.iloc[-1]), 2), "lego": lego, "pattern": pattern, "vol": int(v.iloc[-1])}

def main():
    final_results = {}
    for main_stock, peers in STOCKS_MAP.items():
        try:
            df = yf.download(main_stock, period="60d", interval="1d", progress=False)
            main_data = pro_analysis(df, main_stock)
            main_data['flow'] = get_aastock_flow(main_stock)
            
            # 獲取同業強度 (最高算力橫向對比)
            peer_perf = 0
            for p in peers:
                p_df = yf.download(p, period="2d", interval="1d", progress=False)
                peer_perf += p_df['Close'].pct_change().iloc[-1]
            
            main_data['sector_strength'] = "強於同業" if (df['Close'].pct_change().iloc[-1] > (peer_perf/len(peers))) else "弱於同業"
            final_results[main_stock] = main_data
        except: continue

    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
