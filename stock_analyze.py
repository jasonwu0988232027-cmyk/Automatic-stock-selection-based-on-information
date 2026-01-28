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

# --- 基礎安全設定與環境檢查 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股自動交易選股系統", layout="wide")

DB_FILE = "portfolio.json"

# --- 1. 持倉管理功能 (永久儲存) ---
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

# --- 2. 交易核心邏輯 (進出場條件拆解) ---
def check_trade_logic(ticker, price, rsi, portfolio):
    """
    拆解自 RSI 交易策略:
    - 買入: RSI < 20 且持倉未滿 5 批
    - 賣出: RSI > 80 或 虧損 > 10% (止損)
    """
    trades = portfolio.get(ticker, [])
    avg_cost = sum([t['price'] for t in trades]) / len(trades) if trades else 0
    
    # 買入訊號
    if rsi < 20 and len(trades) < 5:
        return "BUY", "RSI超賣加碼"
        
    # 賣出訊號
    if trades:
        if price < avg_cost * 0.90:  # 止損條件
            return "SELL_ALL", f"觸發止損(成本:{round(avg_cost,2)})"
        if rsi > 80:  # 獲利清倉
            return "SELL_ALL", "RSI過熱獲利"
            
    return "HOLD", "無訊號"

# --- 3. 選股模組 (全市場成交值指標) ---
@st.cache_data(ttl=3600)
def get_tickers():
    # 這裡建議保留您原本 get_full_market_tickers 的邏輯
    return ["2330.TW", "2317.TW", "2454.TW", "2382.TW", "2603.TW", "2881.TW"] # 簡化示範

# --- 4. Streamlit UI 介面 ---
st.title("🤖 台股自動交易監控系統")

# 初始化 Session State 避免重複載入
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 顯示當前持倉摘要表格
st.subheader("💼 當前持倉狀態")
if st.session_state.portfolio:
    summary = []
    for t, t_trades in st.session_state.portfolio.items():
        if t_trades:
            avg = sum([x['price'] for x in t_trades]) / len(t_trades)
            summary.append({"股票代號": t, "持倉批數": len(t_trades), "平均成本": round(avg, 2)})
    if summary:
        st.table(pd.DataFrame(summary))
    else:
        st.info("目前無持倉")
else:
    st.info("目前無持倉")

# 執行按鈕
if st.button("🚀 啟動全市場掃描與訊號檢查", type="primary"):
    all_tickers = get_tickers()
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    # 這裡執行您原本的 fetch_data_full 並過濾 Top 100
    # 為了展示，我們假設掃描完後對名單進行交易判斷
    
    results = []
    for i, ticker in enumerate(all_tickers):
        status_text.text(f"檢查中: {ticker} ({i+1}/{len(all_tickers)})")
        
        # 抓取技術面數據
        df = yf.download(ticker, period="1mo", interval="1d", progress=False)
        if not df.empty:
            df['RSI'] = ta.rsi(df['Close'], length=14)
            curr_price = df['Close'].iloc[-1]
            curr_rsi = df['RSI'].iloc[-1]
            
            action, reason = check_trade_logic(ticker, curr_price, curr_rsi, st.session_state.portfolio)
            
            if action != "HOLD":
                results.append({"股票": ticker, "動作": action, "原因": reason, "價格": round(curr_price, 2)})
                
                # 更新狀態 (模擬交易)
                if action == "BUY":
                    if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                    st.session_state.portfolio[ticker].append({"price": curr_price, "date": str(datetime.now().date())})
                elif action == "SELL_ALL":
                    st.session_state.portfolio[ticker] = []
        
        progress_bar.progress((i + 1) / len(all_tickers))
        time.sleep(1) # 防封鎖延遲
    
    save_portfolio(st.session_state.portfolio) # 存回檔案
    
    if results:
        st.subheader("🚩 今日交易建議")
        st.dataframe(pd.DataFrame(results))
    else:
        st.success("✅ 掃描完成，今日無符合條件之訊號。")
