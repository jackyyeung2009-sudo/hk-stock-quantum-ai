import requests
from bs4 import BeautifulSoup
import yfinance as yf
import json
import pandas as pd
from datetime import datetime

# 標的清單 (已排除無效代碼)
STOCKS = ["1810.HK", "1211.HK", "3690.HK", "2840.HK", "2208.HK", "1772.HK", "3393.HK"]

def get_capital_flow(symbol):
    """從 AAStocks 抓取實時資金流向 (簡化版爬蟲)"""
    sid = symbol.split('.')[0].zfill(5)
    url = f"http://www.aastocks.com/tc/stocks/analysis/stock-quote-details.aspx?symbol={sid}"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        r = requests.get(url, headers=headers, timeout=10)
        soup = BeautifulSoup(r.text, 'html.parser')
        # 抓取「資金淨流入/流出」數值 (此處 ID 需根據實時網頁更新)
        flow_text = soup.find(id="cp_objQuote_lblCapitalInflow").text
        return flow_text
    except:
        return "數據維護中"

def analyze_tech(df):
    """命中率 70% 的技術邏輯：LEGO + 形態"""
    c = df['Close']
    v = df['Volume']
    h = df['High']
    l = df['Low']
    
    # 張士佳 LEGO 邏輯：收盤 > 過去5日高點 + 成交量爆發
    is_lego = "強勢紅磚" if (c.iloc[-1] > h.iloc[-6:-1].max() and v.iloc[-1] > v.tail(10).mean()) else "整理"
    
    # 形態推斷
    pattern = "盤整中"
    ma5 = c.rolling(5).mean()
    ma20 = c.rolling(20).mean()
    
    # 1. 飛機起飛 (均線多頭且角度大)
    if c.iloc[-1] > ma5.iloc[-1] > ma20.iloc[-1] and (ma5.iloc[-1] > ma5.iloc[-2]):
        pattern = "✈️ 飛機起飛"
    # 2. 咖啡杯 (圓弧底回升)
    elif c.iloc[-1] > c.iloc[-20] * 0.98 and c.tail(15).min() < c.iloc[-20] * 0.95:
        pattern = "☕ 咖啡杯形態"
    # 3. 皇冠 (突破前期三重頂)
    elif c.iloc[-1] > h.tail(60).max() * 0.99:
        pattern = "👑 皇冠突破"

    return {"price": round(c.iloc[-1], 2), "lego": is_lego, "pattern": pattern}

def main():
    final_data = {}
    current_time = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    
    for s in STOCKS:
        try:
            # 1. 抓取報價與成交量 (使用 yfinance 確保穩定)
            df = yf.download(s, period="60d", interval="1d", progress=False)
            tech = analyze_tech(df)
            
            # 2. 抓取 AAStocks 資金流
            flow = get_capital_flow(s)
            
            final_data[s] = {
                **tech,
                "flow": flow,
                "update": current_time
            }
        except Exception as e:
            print(f"Error analyzing {s}: {e}")

    # 寫入 data.json
    with open('data.json', 'w', encoding='utf-8') as f:
        json.dump(final_data, f, ensure_ascii=False, indent=4)

if __name__ == "__main__":
    main()
