import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
import numpy as np
from datetime import datetime
import time

# 精確校正後的標的地圖 (100:MINIMAX, 2513:智譜, 3317:迅策)
STOCKS_MAP = {
    "0100.HK": ["2513.HK", "3317.HK"], # AI 板塊
    "1810.HK": ["0700.HK", "9988.HK", "3690.HK"],
    "1211.HK": ["2015.HK", "9868.HK", "9866.HK"],
    "3690.HK": ["9988.HK", "0700.HK", "1024.HK"],
    "1772.HK": ["300750.SZ", "002460.SZ"],
    "3393.HK": ["1088.HK", "0902.HK", "0038.HK"],
    "2208.HK": ["0958.HK", "0916.HK", "1798.HK"],
    "2840.HK": ["GC=F", "PAXG-USD"]
}

def get_aastock_data(symbol):
    """當 yfinance 失效時，強制從 AAStock 爬取基礎報價"""
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'lxml')
        price = soup.find(id="cp_objQuote_lblLastPrice").text
        flow = soup.find(id="cp_objQuote_lblCapitalInflow").text
        vol = soup.find(id="cp_objQuote_lblVolume").text
        return {"price": float(price), "flow": flow.strip(), "volume": vol.strip()}
    except: return None

def analyze_logic(df, fallback_price=None):
    try:
        if df is not None and not df.empty:
            c, v, h, l, o = df['Close'].squeeze(), df['Volume'].squeeze(), df['High'].squeeze(), df['Low'].squeeze(), df['Open'].squeeze()
            price = round(float(c.iloc[-1]), 3)
            # LEGO & 形態判斷 (簡化版以確保穩定)
            lego = "強勢紅磚" if c.iloc[-1] > h.iloc[-6:-1].max() else "整理"
            pattern = "✈️ 飛機起飛" if c.iloc[-1] > c.rolling(5).mean().iloc[-1] else "觀察中"
            vol_str = f"{int(v.iloc[-1]/10000)}萬"
            raw_change = float(c.pct_change().iloc[-1])
        elif fallback_price:
            price = fallback_price['price']
            lego, pattern, vol_str, raw_change = "新股數據同步中", "待觀測", fallback_price['volume'], 0.0
        else: return None

        return {"price": price, "lego": lego, "pattern": pattern, "volume": vol_str, "raw_change": raw_change}
    except: return None

def main():
    final_results = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M")
    names = {"0100.HK": "MINIMAX", "2513.HK": "智譜 AI", "3317.HK": "迅策科技"}

    for main_stock, peers in STOCKS_MAP.items():
        try:
            df = yf.download(main_stock, period="30d", interval="1d", progress=False)
            fallback = get_aastock_data(main_stock) if (df is None or df.empty) else None
            
            res = analyze_logic(df, fallback)
            if not res: continue
            
            # 板塊強度對比
            res['sector_strength'] = "板塊領跑" if res['raw_change'] >= 0 else "板塊跟隨"
            res['flow'] = fallback['flow'] if fallback else "流向計算中"
            res['name'] = names.get(main_stock, "")
            res['update'] = current_time
            final_results[main_stock] = res
            time.sleep(1)
        except: continue
    
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_results, f, ensure_ascii=False, indent=4)
    print("✅ 算力引擎已強制更新 data.json")

if __name__ == "__main__":
    main()
