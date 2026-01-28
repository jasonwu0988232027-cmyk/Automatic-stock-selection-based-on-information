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

# --- 基礎設定與環境檢查 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全市場自動交易系統 (RSI-7)", layout="wide")

DB_FILE = "portfolio.json"

# --- 1. 持倉管理功能 (JSON) ---
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

# --- 2. 交易核心邏輯 (RSI 週期已調整為 7) ---
def check_trade_logic(ticker, price, rsi, portfolio):
    # 防錯檢查：確保 RSI 為有效數字
    if rsi is None or pd.isna(rsi):
        return "HOLD", "指標數據計算中"
    
    rsi_val = float(rsi)
    trades = portfolio.get(ticker, [])
    
    # 計算平均持倉成本
    avg_cost = sum([float(t['price']) for t in trades]) / len(trades) if trades else 0
    
    # --- 買進訊號 (RSI 週期 7) ---
    # RSI < 20 (短線超賣) 且 該股持倉未滿 5 批
    if rsi_val < 20 and len(trades) < 5:
        return "BUY", "RSI-7 短線超賣加碼"
        
    # --- 賣出訊號 ---
    if trades:
        # 1. 硬止損: 虧損達 10%
        if price < avg_cost * 0.90:
            return "SELL_ALL", f"觸發止損(成本:{round(avg_cost,2)})"
        
        # 2. 獲利清倉: RSI > 80 (短線過熱)
        if rsi_val > 80:
            return "SELL_ALL", "RSI-7 短線過熱止盈"
            
    return "HOLD", "觀望"

# --- 3. 選股模組 (延用您提供的完整 1000 隻核心清單) ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    # 這裡延用您提供的完整核心代碼
    base_codes = [
        "1101", "1102", "1216", "1301", "1303", "1319", "1326", "1402", "1434", "1476", "1477", "1503", "1504", "1513", "1519", "1590", "1605", "1608", "1609", "1707", "1717", "1722", "1723", "1795", "1802", "1904", "2002", "2006", "2014", "2027", "2031", "2101", "2105", "2201", "2204", "2206", "2301", "2303", "2308", "2313", "2317", "2324", "2327", "2330", "2337", "2344", "2345", "2347", "2351", "2352", "2353", "2354", "2356", "2357", "2360", "2368", "2371", "2376", "2377", "2379", "2382", "2383", "2385", "2393", "2395", "2401", "2408", "2409", "2412", "2421", "2449", "2451", "2454", "2457", "2458", "2474", "2480", "2492", "2498", "2542", "2603", "2606", "2609", "2610", "2615", "2618", "2633", "2634", "2637", "2707", "2801", "2809", "2812", "2834", "2880", "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889", "2890", "2891", "2892", "2903", "2912", "3006", "3008", "3017", "3023", "3034", "3035", "3037", "3044", "3045", "3189", "3231", "3406", "3443", "3481", "3532", "3533", "3583", "3653", "3661", "3702", "3711", "3714", "4915", "4919", "4938", "4958", "4961", "4967", "5269", "5434", "5871", "5876", "5880", "6005", "6176", "6213", "6239", "6285", "6409", "6415", "6446", "6505", "6515", "6669", "6719", "6770", "8046", "8069", "8081", "8454", "8464", "9904", "9910", "9921", "9945"
    ]
    extended_list = [f"{str(i).zfill(4)}.TW" for i in range(1101, 9999)]
    return [t for t in extended_list if t.split('.')[0] in base_codes or int(t.split('.')[0]) < 3000]

def fetch_market_rank(tickers):
    all_res = []
    batch_size = 20
    p_bar = st.progress(0)
    status = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status.text(f"🔍 掃描全市場成交值指標: {i} / {len(tickers)}...")
        try:
            # 獲取最新數據進行排名
            df = yf.download(batch, period="2d", group_by='ticker', threads=False, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        val = round((float(last['Close']) * float(last['Volume'])) / 100_000_000, 2)
                        if val > 0.1:
                            all_res.append({"股票代號": t, "收盤價": round(float(last['Close']), 2), "成交值指標": val})
                except: continue
        except: pass
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    status.empty()
    return pd.DataFrame(all_res)

# --- 4. Streamlit 主介面 ---
st.title("🤖 台股全市場自動交易系統 (RSI-7)")

# 初始化持倉紀錄
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 顯示當前持倉摘要
with st.expander("💼 目前持倉紀錄", expanded=True):
    p_sum = []
    for t, t_trades in st.session_state.portfolio.items():
        if t_trades:
            avg = sum([x['price'] for x in t_trades]) / len(t_trades)
            p_sum.append({"股票代號": t, "持倉批數": len(t_trades), "平均成本": round(avg, 2)})
    if p_sum:
        st.dataframe(pd.DataFrame(p_sum), use_container_width=True)
    else:
        st.info("目前無持倉部位。")

# 啟動按鈕
if st.button("🚀 開始全市場深度檢查 (成交值排行 + RSI-7 訊號)", type="primary"):
    all_list = get_full_market_tickers()
    
    # 步驟 1: 找出成交值指標 Top 100
    df_raw = fetch_market_rank(all_list)
    if not df_raw.empty:
        top_100 = df_raw.sort_values("成交值指標", ascending=False).head(100)
        st.success(f"✅ 已篩選出前 100 名資金熱點標的，開始計算 RSI-7...")
        
        # 步驟 2: 對 Top 100 進行策略判斷
        results = []
        trade_pbar = st.progress(0)
        
        for idx, row in enumerate(top_100.itertuples()):
            ticker = row.股票代號
            try:
                # 抓取數據計算 RSI(7)
                hist = yf.download(ticker, period="1mo", interval="1d", progress=False)
                if len(hist) < 10: continue # 確保有足夠數據算 RSI-7
                
                # 計算 RSI 週期 = 7
                hist['RSI'] = ta.rsi(hist['Close'], length=7)
                
                curr_p = float(hist['Close'].iloc[-1])
                curr_rsi = hist['RSI'].iloc[-1]
                
                action, reason = check_trade_logic(ticker, curr_p, curr_rsi, st.session_state.portfolio)
                
                if action != "HOLD":
                    results.append({
                        "股票": ticker, "動作": action, "原因": reason, 
                        "價格": round(curr_p, 2), "RSI-7": round(curr_rsi, 2)
                    })
                    
                    # 紀錄至 Session
                    if action == "BUY":
                        if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                        st.session_state.portfolio[ticker].append({"price": curr_p, "date": str(datetime.now().date())})
                    elif action == "SELL_ALL":
                        st.session_state.portfolio[ticker] = []
            except: continue
            trade_pbar.progress((idx + 1) / 100)
            
        save_portfolio(st.session_state.portfolio) # 存回 JSON
        
        if results:
            st.subheader("🚩 今日觸發訊號建議")
            st.table(pd.DataFrame(results))
        else:
            st.success("🏁 掃描完成，今日無符合 RSI-7 買賣條件之訊號。")
    else:
        st.error("掃描出錯，請檢查 Yahoo Finance 連線狀態。")
