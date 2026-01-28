import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import json
import os
import time
import requests
import urllib3
from datetime import datetime

# --- 基礎設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股量化監控系統", layout="wide")

DB_FILE = "portfolio.json"

# --- 1. 持倉管理 ---
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- 2. 側邊欄：參數調整區 ---
st.sidebar.header("⚙️ 策略參數設定")
rsi_p = st.sidebar.slider("RSI 計算週期", 3, 14, 7)
buy_rsi = st.sidebar.slider("買入門檻 (RSI 低於)", 10, 40, 20)
sell_rsi = st.sidebar.slider("止盈門檻 (RSI 高於)", 60, 90, 80)
sl_pct = st.sidebar.slider("硬止損比例 (%)", 5, 20, 10) / 100

st.sidebar.divider()
st.sidebar.info(f"當前模式：RSI-{rsi_p}\n目標：<{buy_rsi} 買入 / >{sell_rsi} 賣出")

# --- 3. 交易邏輯函數 ---
def check_trade_logic(ticker, price, rsi, portfolio):
    if rsi is None or pd.isna(rsi): return "HOLD", "指標計算中"
    
    rsi_val = float(rsi)
    trades = portfolio.get(ticker, [])
    avg_cost = sum([float(t['price']) for t in trades]) / len(trades) if trades else 0
    
    # 買入
    if rsi_val < buy_rsi and len(trades) < 5:
        return "BUY", f"RSI-{rsi_p} 超跌 ({round(rsi_val,1)})"
    
    # 賣出
    if trades:
        if price < avg_cost * (1 - sl_pct):
            return "SELL_ALL", f"觸發 {int(sl_pct*100)}% 止損"
        if rsi_val > sell_rsi:
            return "SELL_ALL", f"RSI-{rsi_p} 過熱 ({round(rsi_val,1)})"
            
    return "HOLD", "觀望"

# --- 4. 選股模組 (1000隻代碼) ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    base_codes = ["1101", "1102", "1216", "1301", "1303", "2002", "2303", "2317", "2330", "2382", "2454", "2603", "2881", "3008", "3231", "3711", "6669"] # 簡化示範，請填入完整1000隻
    extended_list = [f"{str(i).zfill(4)}.TW" for i in range(1101, 9999)]
    return [t for t in extended_list if t.split('.')[0] in base_codes or int(t.split('.')[0]) < 3000]

def fetch_rank(tickers):
    all_res = []
    p_bar = st.progress(0, text="正在獲取市場成交值...")
    for i in range(0, len(tickers), 30):
        batch = tickers[i:i+30]
        try:
            df = yf.download(batch, period="2d", group_by='ticker', threads=True, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        val = (float(last['Close']) * float(last['Volume'])) / 1e8
                        all_res.append({"股票代號": t, "收盤價": float(last['Close']), "成交值(億)": val})
                except: continue
        except: pass
        p_bar.progress(min((i+30)/len(tickers), 1.0))
    return pd.DataFrame(all_res)

# --- 5. 主介面 ---
st.title("📊 台股即時監控與自動策略系統")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 持倉顯示
with st.expander("💼 持倉紀錄摘要", expanded=False):
    summary = [{"股票": t, "批數": len(v), "成本": round(sum([x['price'] for x in v])/len(v), 2)} 
               for t, v in st.session_state.portfolio.items() if v]
    st.table(pd.DataFrame(summary)) if summary else st.write("尚無持倉")

if st.button("🚀 執行全市場掃描", type="primary"):
    all_list = get_full_market_tickers()
    df_rank = fetch_rank(all_list)
    
    if not df_rank.empty:
        top_100 = df_rank.sort_values("成交值(億)", ascending=False).head(100)
        
        # --- Debug 監視面板：顯示前 10 名即時 RSI ---
        st.subheader(f"📡 Top 10 熱門股 RSI-{rsi_p} 實時監測")
        monitor_cols = st.columns(5)
        
        results = []
        scan_bar = st.progress(0, text="正在計算技術指標...")
        
        for idx, row in enumerate(top_100.itertuples()):
            ticker = row.股票代號
            hist = yf.download(ticker, period="1mo", interval="1d", progress=False)
            if len(hist) < rsi_p + 5: continue
            
            hist['RSI'] = ta.rsi(hist['Close'], length=rsi_p)
            curr_p = float(hist['Close'].iloc[-1])
            curr_rsi = hist['RSI'].iloc[-1]
            
            # 顯示前 10 名狀態
            if idx < 10:
                with monitor_cols[idx % 5]:
                    st.metric(label=ticker, value=f"{curr_p:.1f}", delta=f"RSI: {curr_rsi:.1f}", delta_color="inverse" if curr_rsi > 70 else "normal")

            # 策略判斷
            action, reason = check_trade_logic(ticker, curr_p, curr_rsi, st.session_state.portfolio)
            if action != "HOLD":
                results.append({"股票": ticker, "動作": action, "原因": reason, "價格": curr_p, "RSI": round(curr_rsi, 2)})
                if action == "BUY":
                    if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                    st.session_state.portfolio[ticker].append({"price": curr_p, "date": str(datetime.now().date())})
                elif action == "SELL_ALL":
                    st.session_state.portfolio[ticker] = []
            
            scan_bar.progress((idx + 1) / 100)
        
        save_portfolio(st.session_state.portfolio)
        
        if results:
            st.subheader("🚩 策略觸發訊號")
            st.dataframe(pd.DataFrame(results), use_container_width=True)
        else:
            st.success(f"🏁 掃描完成。Top 100 標的中，無標的低於 {buy_rsi} 或高於 {sell_rsi}。")
