import yfinance as yf
import json
import pandas as pd

# 定義標的 (HK 股代號後加 .HK)
stocks = ["1810.HK", "1211.HK", "3690.HK", "2840.HK", "2208.HK", "1772.HK", "3393.HK", "0100.HK", "2513.HK"]

def analyze_patterns(df):
    # 簡單示例：咖啡杯形態邏輯 (需搭配最高算力精確化)
    is_cup = df['Close'].tail(20).min() < df['Close'].tail(50).mean() # 簡化邏輯
    # LEGO 邏輯：判定當前是否為強勢磚
    is_lego_strong = df['Close'].iloc[-1] > df['Close'].iloc[-2] and df['Volume'].iloc[-1] > df['Volume'].mean()
    
    return {
        "price": round(df['Close'].iloc[-1], 2),
        "change": str(round((df['Close'].pct_change().iloc[-1] * 100), 2)) + "%",
        "lego": "強勢紅磚" if is_lego_strong else "整理平盤",
        "pattern": "飛機起飛" if is_lego_strong and is_cup else "觀察中"
    }

results = {}
for symbol in stocks:
    data = yf.download(symbol, period="3mo", interval="1d")
    results[symbol] = analyze_patterns(data)

# 將結果寫入 json 供網頁讀取
with open('data.json', 'w') as f:
    json.dump(results, f)
