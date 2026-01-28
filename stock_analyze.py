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
st.set_page_config(page_title="台股量化選股與交易系統", layout="wide")

DB_FILE = "portfolio.json"

# --- 1. 資料管理功能 ---
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# --- 2. 核心組件：選股清單 ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    # 延用您提供的 1000 隻核心清單逻辑
    base_codes = ["1101", "1102", "1216", "2330", "2317", "2454", "2603", "2881", "2882"] # 建議補足完整清單
    extended_list = [f"{str(i).zfill(4)}.TW" for i in range(1101, 9999)]
    return [t for t in extended_list if t.split('.')[0] in base_codes or int(t.split('.')[0]) < 3000]

# --- 3. 頁面導覽 ---
page = st.sidebar.radio("導覽選單", ["1. 全市場資金選股", "2. RSI 交易決策與持倉"])

# --- 策略參數設定 ---
st.sidebar.divider()
st.sidebar.header("⚙️ RSI 策略參數")
rsi_p = st.sidebar.slider("RSI 週期", 3, 14, 7)
buy_rsi = st.sidebar.slider("買入線 (RSI <)", 10, 40, 25)
sell_rsi = st.sidebar.slider("賣出線 (RSI >)", 60, 95, 75)

# --- 頁面 1：全市場資金選股 ---
if page == "1. 全市場資金選股":
    st.title("🏆 全市場資金熱點排行")
    st.markdown("依據「成交值指標」從 1000+ 隻股票中篩選出前 100 名。")
    
    if st.button("🚀 執行全市場掃描", type="primary"):
        all_list = get_full_market_tickers()
        res_rank = []
        p_bar = st.progress(0, text="正在計算成交值...")
        
        batch_size = 30
        for i in range(0, len(all_list), batch_size):
            batch = all_list[i : i + batch_size]
            df = yf.download(batch, period="2d", group_by='ticker', threads=True, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        val = (float(last['Close']) * float(last['Volume'])) / 1e8
                        res_rank.append({"股票代號": t, "收盤價": float(last['Close']), "成交值(億)": val})
                except: continue
            p_bar.progress(min((i + batch_size) / len(all_list), 1.0))
        
        if res_rank:
            top_100 = pd.DataFrame(res_rank).sort_values("成交值(億)", ascending=False).head(100)
            st.session_state.top_100_list = top_100['股票代號'].tolist()
            st.success("✅ 掃描完成！Top 100 已存入快取，請切換至第二頁查看交易訊號。")
            st.dataframe(top_100, use_container_width=True)
        else:
            st.error("掃描失敗，請檢查網路連線。")

# --- 頁面 2：RSI 交易決策與持倉 ---
elif page == "2. RSI 交易決策與持倉":
    st.title("🤖 RSI 智能交易決策")
    
    if 'top_100_list' not in st.session_state:
        st.warning("⚠️ 請先在第一頁執行掃描以獲取熱點標的。")
    else:
        st.subheader("📡 Top 100 標的即時訊號檢查")
        
        results = []
        p_check = st.progress(0, text="正在分析 RSI 訊號...")
        
        for idx, ticker in enumerate(st.session_state.top_100_list):
            try:
                hist = yf.download(ticker, period="1mo", interval="1d", progress=False)
                if len(hist) < rsi_p + 2: continue
                
                hist['RSI'] = ta.rsi(hist['Close'], length=rsi_p)
                curr_p = float(hist['Close'].iloc[-1])
                curr_rsi = hist['RSI'].iloc[-1]
                
                # 持倉檢查與訊號判斷
                action = "觀望"
                is_held = ticker in st.session_state.portfolio and st.session_state.portfolio[ticker]
                
                if curr_rsi < buy_rsi:
                    action = "🔔 建議買入"
                elif curr_rsi > sell_rsi and is_held:
                    action = "⚠️ 建議賣出"
                
                if action != "觀望":
                    results.append({"股票代號": ticker, "目前價格": round(curr_p, 2), "RSI": round(curr_rsi, 1), "建議動作": action})
            except: continue
            p_check.progress((idx + 1) / len(st.session_state.top_100_list))
        
        if results:
            df_res = pd.DataFrame(results)
            st.table(df_res)
            
            # 買賣操作模擬
            st.divider()
            st.subheader("🛒 手動更新持倉")
            c1, c2, c3 = st.columns(3)
            with c1: t_input = st.selectbox("選擇股票", df_res['股票代號'])
            with c2: p_input = st.number_input("成交價格", value=0.0)
            with c3:
                if st.button("➕ 確認購入並加入持倉"):
                    if t_input not in st.session_state.portfolio: st.session_state.portfolio[t_input] = []
                    st.session_state.portfolio[t_input].append({"price": p_input, "date": str(datetime.now().date())})
                    save_portfolio(st.session_state.portfolio)
                    st.rerun()

        else:
            st.info("目前 Top 100 標的中無符合 RSI 買賣門檻的訊號。")

    # --- 持倉紀錄區 ---
    st.divider()
    st.subheader("💼 我的持倉紀錄")
    p_summary = []
    for t, trades in st.session_state.portfolio.items():
        if trades:
            avg_cost = sum([x['price'] for x in trades]) / len(trades)
            p_summary.append({"股票代號": t, "持倉批數": len(trades), "平均成本": round(avg_cost, 2)})
    
    if p_summary:
        df_p = pd.DataFrame(p_summary)
        st.dataframe(df_p, use_container_width=True)
        clear_t = st.selectbox("清空持倉標的", df_p['股票代號'])
        if st.button("🗑️ 確認賣出(移除持倉)"):
            st.session_state.portfolio[clear_t] = []
            save_portfolio(st.session_state.portfolio)
            st.rerun()
    else:
        st.write("目前尚無持倉紀錄。")
