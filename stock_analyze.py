import streamlit as st
import yfinance as yf
import pandas as pd
from datetime import datetime

# 使用 Streamlit 快取，設定 1 小時 (3600秒) 更新一次即可
@st.cache_data(ttl=3600)
def get_top_gainers():
    """獲取台股漲幅排行 (優化版)"""
    tickers = ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW", 
               "2412.TW", "2881.TW", "2882.TW", "2603.TW", "3008.TW"]
    
    # 使用 yf.download 一次性抓取所有股票的 2 天歷史數據，減少請求次數
    df_all = yf.download(tickers, period="2d", group_by='ticker', progress=False)
    
    data_list = []
    for t in tickers:
        try:
            # 獲取該股票的兩日收盤價
            hist = df_all[t]
            if len(hist) >= 2:
                close_now = hist['Close'].iloc[-1]
                close_before = hist['Close'].iloc[-2]
                change = (close_now - close_before) / close_before * 100
                
                data_list.append({
                    "代碼": t,
                    "名稱": t, # 暫時用代碼代替，避免調用 stock.info 導致限流
                    "現價": round(close_now, 2),
                    "漲幅%": round(change, 2)
                })
        except Exception as e:
            continue
    
    # 依照漲幅排序
    df_result = pd.DataFrame(data_list).sort_values(by="漲幅%", ascending=False).head(10)
    return df_result
