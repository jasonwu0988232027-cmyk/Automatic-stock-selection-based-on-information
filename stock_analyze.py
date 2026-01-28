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
st.set_page_config(page_title="台股全市場自動交易系統", layout="wide")

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

# --- 2. 交易核心邏輯 (修正版) ---
def check_trade_logic(ticker, price, rsi, portfolio):
    if rsi is None or pd.isna(rsi):
        return "HOLD", "指標數據不足"
    
    rsi_val = float(rsi)
    trades = portfolio.get(ticker, [])
    
    # 計算平均成本 (防錯)
    avg_cost = sum([float(t['price']) for t in trades]) / len(trades) if trades else 0
    
    # 買進: RSI < 20 (超賣) 且持倉未滿 5 批
    if rsi_val < 20 and len(trades) < 5:
        return "BUY", "RSI超賣加碼"
        
    # 賣出邏輯
    if trades:
        # 1. 止損: 虧損 > 10%
        if price < avg_cost * 0.90:
            return "SELL_ALL", f"觸發止損(成本:{round(avg_cost,2)})"
        # 2. 獲利清倉: RSI > 80
        if rsi_val > 80:
            return "SELL_ALL", "RSI過熱獲利出清"
            
    return "HOLD", "觀望"

# --- 3. 選股模組 (1000+ 內建清單) ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    base_codes = [
        "1101", "1102", "1216", "1301", "1303", "1319", "2002", "2303", "2308", "2317", "2330", "2382", "2412", "2454", "2603", "2609", "2881", "2882", "2891", "3008", "3017", "3231", "3711", "5871", "6669"
        # ... (此處可延用您原本 1000 隻的 base_codes)
    ]
    extended_list = [f"{str(i).zfill(4)}.TW" for i in range(1101, 9999)]
    return [t for t in extended_list if t.split('.')[0] in base_codes or int(t.split('.')[0]) < 2500]

def fetch_stock_rank(tickers):
    all_res = []
    batch_size = 20
    p_bar = st.progress(0)
    status = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status.text(f"🔍 掃描全市場資金指標: {i}/{len(tickers)}...")
        try:
            df = yf.download(batch, period="2d", group_by='ticker', threads=False, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        val = round((float(last['Close']) * float(last['Volume'])) / 1e8, 2)
                        if val > 0.1:
                            all_res.append({"股票代號": t, "收盤價": float(last['Close']), "成交值指標": val})
                except: continue
        except: pass
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    status.empty()
    return pd.DataFrame(all_res)

# --- 4. 主介面 ---
st.title("🤖 台股全市場自動交易監控系統")

# 初始化與載入持倉
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 顯示目前持倉
with st.expander("💼 我的持倉紀錄", expanded=True):
    p_summary = []
    for t, t_trades in st.session_state.portfolio.items():
        if t_trades:
            avg = sum([x['price'] for x in t_trades]) / len(t_trades)
            p_summary.append({"股票代號": t, "持倉批數": len(t_trades), "平均成本": round(avg, 2)})
    if p_summary:
        st.dataframe(pd.DataFrame(p_summary), use_container_width=True)
    else:
        st.info("目前無持倉部位")

# 執行深度掃描
if st.button("🚀 啟動全市場深度掃描與訊號檢查", type="primary"):
    all_list = get_full_market_tickers()
    
    # 步驟 1: 選股 (依成交值指標排序)
    df_rank = fetch_stock_rank(all_list)
    if not df_rank.empty:
        top_100 = df_rank.sort_values("成交值指標", ascending=False).head(100)
        st.success(f"✅ 已選出成交值前 100 名，開始檢查 RSI 訊號...")
        
        # 步驟 2: 對 Top 100 進行交易訊號檢查
        results = []
        trade_pbar = st.progress(0)
        
        for idx, row in enumerate(top_100.itertuples()):
            ticker = row.股票代號
            try:
                hist = yf.download(ticker, period="2mo", interval="1d", progress=False)
                if len(hist) < 20: continue
                
                # [cite_start]計算 RSI(14) [cite: 1]
                hist['RSI'] = ta.rsi(hist['Close'], length=14)
                
                curr_p = float(hist['Close'].iloc[-1])
                curr_rsi = hist['RSI'].iloc[-1]
                
                # 執行策略判斷
                action, reason = check_trade_logic(ticker, curr_p, curr_rsi, st.session_state.portfolio)
                
                if action != "HOLD":
                    results.append({"股票": ticker, "動作": action, "原因": reason, "價格": round(curr_p, 2), "RSI": round(curr_rsi, 2)})
                    
                    # 更新模擬持倉
                    if action == "BUY":
                        if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                        st.session_state.portfolio[ticker].append({"price": curr_p, "date": str(datetime.now().date())})
                    elif action == "SELL_ALL":
                        st.session_state.portfolio[ticker] = []
            except: continue
            trade_pbar.progress((idx + 1) / 100)
            
        save_portfolio(st.session_state.portfolio)
        
        if results:
            st.subheader("🚩 今日交易建議清單")
            st.table(pd.DataFrame(results))
        else:
            st.success("🏁 掃描完畢，Top 100 標的中今日無符合條件之訊號。")
    else:
        st.error("掃描失敗，請檢查網路。")
