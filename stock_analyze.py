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

# --- 基礎設定與防錯 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全市場自動交易監控", layout="wide")

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

# --- 2. 交易核心邏輯 (修正 TypeError 並加入止損/止盈) ---
def check_trade_logic(ticker, price, rsi, portfolio):
    if rsi is None or pd.isna(rsi):
        return "HOLD", "指標無數據"
    
    rsi_val = float(rsi)
    trades = portfolio.get(ticker, [])
    
    # 計算平均持倉成本
    avg_cost = sum([float(t['price']) for t in trades]) / len(trades) if trades else 0
    
    # --- 買進訊號 ---
    # RSI < 20 (極度超賣) 且 該股持倉未滿 5 批
    if rsi_val < 20 and len(trades) < 5:
        return "BUY", "RSI超賣加碼"
        
    # --- 賣出訊號 ---
    if trades:
        # 1. 硬止損: 虧損達 10%
        if price < avg_cost * 0.90:
            return "SELL_ALL", f"觸發止損(成本:{round(avg_cost,2)})"
        
        # 2. 獲利清倉: RSI > 80 (極度過熱)
        if rsi_val > 80:
            return "SELL_ALL", "RSI過熱止盈"
            
    return "HOLD", "觀望"

# --- 3. 選股模組 (延用完整的 1000 隻 base_codes) ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    # 這裡填入您原本提供的完整 1000 隻核心代碼
    base_codes = [
        "1101", "1102", "1216", "1301", "1303", "1319", "1326", "1402", "1434", "1476", "1477", "1503", "1504", "1513", "1519", "1590", "1605", "1608", "1609", "1707", "1717", "1722", "1723", "1795", "1802", "1904", "2002", "2006", "2014", "2027", "2031", "2101", "2105", "2201", "2204", "2206", "2301", "2303", "2308", "2313", "2317", "2324", "2327", "2330", "2337", "2344", "2345", "2347", "2351", "2352", "2353", "2354", "2356", "2357", "2360", "2368", "2371", "2376", "2377", "2379", "2382", "2383", "2385", "2393", "2395", "2401", "2408", "2409", "2412", "2421", "2449", "2451", "2454", "2457", "2458", "2474", "2480", "2492", "2498", "2542", "2603", "2606", "2609", "2610", "2615", "2618", "2633", "2634", "2637", "2707", "2801", "2809", "2812", "2834", "2880", "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889", "2890", "2891", "2892", "2903", "2912", "3006", "3008", "3017", "3023", "3034", "3035", "3037", "3044", "3045", "3189", "3231", "3406", "3443", "3481", "3532", "3533", "3583", "3653", "3661", "3702", "3711", "3714", "4915", "4919", "4938", "4958", "4961", "4967", "5269", "5434", "5871", "5876", "5880", "6005", "6176", "6213", "6239", "6285", "6409", "6415", "6446", "6505", "6515", "6669", "6719", "6770", "8046", "8069", "8081", "8454", "8464", "9904", "9910", "9921", "9945"
    ]
    extended_list = [f"{str(i).zfill(4)}.TW" for i in range(1101, 9999)]
    # 回傳包含 1000 隻核心股以及代號 3000 以下的所有標的，確保廣度
    return [t for t in extended_list if t.split('.')[0] in base_codes or int(t.split('.')[0]) < 3000]

def fetch_data_and_rank(tickers):
    all_res = []
    batch_size = 20
    p_bar = st.progress(0)
    status = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status.text(f"⏳ 正在掃描全市場資金指標: {i} / {len(tickers)}...")
        try:
            df = yf.download(batch, period="2d", group_by='ticker', threads=False, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        val = round((float(last['Close']) * float(last['Volume'])) / 100_000_000, 2)
                        if val > 0.1:
                            all_res.append({
                                "股票代號": t, 
                                "收盤價": round(float(last['Close']), 2), 
                                "成交值指標": val
                            })
                except: continue
        except: pass
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    status.empty()
    return pd.DataFrame(all_res)

# --- 4. 主介面 (UI) ---
st.title("📊 台股全市場自動交易監控系統")

# 初始化持倉
if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 顯示當前持倉狀態
with st.expander("💼 我的持倉紀錄 (JSON 加載)", expanded=True):
    summary_list = []
    for t, t_trades in st.session_state.portfolio.items():
        if t_trades:
            avg = sum([x['price'] for x in t_trades]) / len(t_trades)
            summary_list.append({"股票代號": t, "持倉批數": len(t_trades), "平均成本": round(avg, 2)})
    if summary_list:
        st.dataframe(pd.DataFrame(summary_list), use_container_width=True)
    else:
        st.info("目前無任何持倉部位。")

# 執行深度掃描按鈕
if st.button("🚀 啟動全市場深度掃描與自動交易判斷", type="primary"):
    all_list = get_full_market_tickers()
    
    # 步驟 1: 先選股 (找出成交值前 100)
    df_raw = fetch_data_and_rank(all_list)
    if not df_raw.empty:
        top_100 = df_raw.sort_values("成交值指標", ascending=False).head(100)
        st.success(f"✅ 已選出成交值前 100 名，開始對精選股進行 RSI 訊號檢查...")
        
        # 步驟 2: 對這 100 名標的計算 RSI 並判斷進出場
        results = []
        trade_pbar = st.progress(0)
        
        for idx, row in enumerate(top_100.itertuples()):
            ticker = row.股票代號
            try:
                # 抓取一個月數據計算 RSI(14)
                hist = yf.download(ticker, period="1mo", interval="1d", progress=False)
                if len(hist) < 15: continue
                
                hist['RSI'] = ta.rsi(hist['Close'], length=14)
                curr_price = float(hist['Close'].iloc[-1])
                curr_rsi = hist['RSI'].iloc[-1]
                
                action, reason = check_trade_logic(ticker, curr_price, curr_rsi, st.session_state.portfolio)
                
                if action != "HOLD":
                    results.append({
                        "股票代號": ticker, 
                        "動作": action, 
                        "原因": reason, 
                        "目前價格": round(curr_price, 2), 
                        "RSI": round(curr_rsi, 2) if not pd.isna(curr_rsi) else "N/A"
                    })
                    
                    # 更新模擬帳戶狀態
                    if action == "BUY":
                        if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                        st.session_state.portfolio[ticker].append({"price": curr_price, "date": str(datetime.now().date())})
                    elif action == "SELL_ALL":
                        st.session_state.portfolio[ticker] = []
            except: continue
            trade_pbar.progress((idx + 1) / 100)
            
        save_portfolio(st.session_state.portfolio)
        
        if results:
            st.subheader("🚩 今日自動交易訊號建議")
            st.table(pd.DataFrame(results))
        else:
            st.success("🏁 掃描完畢，成交值前 100 名中今日無符合條件之訊號。")
    else:
        st.error("❌ 無法獲取市場數據，請檢查網路連線。")

st.divider()
st.caption("選股策略：全市場成交值指標 Top 100 | 交易策略：RSI(14) < 20 買入, > 80 賣出, 止損 10%")
