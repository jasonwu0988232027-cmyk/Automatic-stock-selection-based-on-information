import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import os
import time
import random
import requests
import urllib3
from datetime import datetime

# --- 基礎設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股自動交易選股系統", layout="wide")

DB_FILE = "portfolio.json"

# --- 1. 持倉管理 (JSON) ---
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f:
                return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f:
        json.dump(data, f, indent=4)

# --- 2. 交易核心邏輯 (修正 TypeError) ---
def check_trade_logic(ticker, price, rsi, portfolio):
    # 防錯機制：確保 rsi 不是 None 且是有效數字
    if rsi is None or pd.isna(rsi):
        return "HOLD", "指標無數據"
    
    # 確保 rsi 轉為純浮點數
    rsi_val = float(rsi)
    
    trades = portfolio.get(ticker, [])
    # 修正：計算平均成本時也要防錯
    if trades:
        avg_cost = sum([float(t['price']) for t in trades]) / len(trades)
    else:
        avg_cost = 0
    
    # 買入: RSI < 20 且持倉未滿 5 批
    if rsi_val < 20 and len(trades) < 5:
        return "BUY", "RSI超賣加碼"
        
    # 賣出: RSI > 80 或 虧損 > 10%
    if trades:
        if price < avg_cost * 0.90:
            return "SELL_ALL", f"觸發止損(成本:{round(avg_cost,2)})"
        if rsi_val > 80:
            return "SELL_ALL", "RSI過熱獲利"
            
    return "HOLD", "觀望"

# --- 3. 選股模組 (請保留您原本的 get_full_market_tickers 函數內容) ---
# [此處置入您的 get_full_market_tickers 與 fetch_data_full]

# --- 4. Streamlit 主介面 ---
st.title("🤖 台股自動交易監控系統")

# 初始化 Session State
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 顯示持倉
st.subheader("💼 當前持倉狀態")
summary_data = []
for t, t_trades in st.session_state.portfolio.items():
    if t_trades:
        avg = sum([x['price'] for x in t_trades]) / len(t_trades)
        summary_data.append({"股票代號": t, "持倉批數": len(t_trades), "平均成本": round(avg, 2)})

if summary_data:
    st.dataframe(pd.DataFrame(summary_data), use_container_width=True)
else:
    st.info("目前無持有部位")

# 執行與掃描
if st.button("🚀 啟動深度掃描與訊號檢查", type="primary"):
    # 此處調用選股清單
    all_tickers = ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "2603.TW", "2881.TW"] # 示例，請用 get_full_market_tickers()
    
    progress_bar = st.progress(0)
    results = []
    
    for i, ticker in enumerate(all_tickers):
        try:
            # 確保抓取足夠天數(1mo)以計算 RSI(14) 
            df = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if df.empty or len(df) < 14: continue
            
            # 使用 pandas_ta 計算 RSI
            df['RSI'] = ta.rsi(df['Close'], length=14)
            
            # 取最後一個值，並確保排除 NaN
            curr_price = float(df['Close'].iloc[-1])
            curr_rsi = df['RSI'].iloc[-1]
            
            action, reason = check_trade_logic(ticker, curr_price, curr_rsi, st.session_state.portfolio)
            
            if action != "HOLD":
                results.append({"股票": ticker, "動作": action, "原因": reason, "價格": round(curr_price, 2)})
                
                # 更新 Session 持倉
                if action == "BUY":
                    if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                    st.session_state.portfolio[ticker].append({"price": curr_price, "date": str(datetime.now().date())})
                elif action == "SELL_ALL":
                    st.session_state.portfolio[ticker] = []
                    
        except Exception as e:
            continue
        
        progress_bar.progress((i + 1) / len(all_tickers))
    
    save_portfolio(st.session_state.portfolio)
    st.session_state.portfolio = load_portfolio() # 重新整理狀態
    
    if results:
        st.subheader("🚩 今日交易建議")
        st.table(pd.DataFrame(results))
    else:
        st.success("✅ 檢查完畢，今日無訊號。")
