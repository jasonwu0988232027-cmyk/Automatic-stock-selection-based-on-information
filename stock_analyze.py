import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import time
import random
import requests
import urllib3
import json
import os
from datetime import datetime

# --- 基礎配置 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股多因子量化交易系統", layout="wide")

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

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# --- 2. 核心選股模組：採用您最全面的掃描方式 ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    """從證交所獲取最完整清單，失敗則啟動內建 1000+ 隻保險清單"""
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    try:
        res = requests.get(url, timeout=10, verify=False, headers={'User-Agent': 'Mozilla/5.0'})
        res.encoding = 'big5'
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        tickers = [f"{t.split('  ')[0].strip()}.TW" for t in df['有價證券代號及名稱'] if len(t.split('  ')[0].strip()) == 4]
        if len(tickers) > 800: return tickers
    except:
        pass
    
    # 保險清單 (部分列出)
    return [f"{i:04d}.TW" for i in range(1101, 9999)] # 簡化代表，實際會執行全面掃描

# --- 3. 多因子評分邏輯 ---
def analyze_stock(ticker, weights):
    """整合 RSI, MA, 波動率, 與爆量因子"""
    try:
        df = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # 計算指標
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        curr, prev = df.iloc[-1], df.iloc[-2]
        score = 0
        reasons = []

        # RSI 超賣因子
        if float(curr['RSI']) < 30: 
            score += weights['rsi']; reasons.append("RSI超賣")
        
        # MA 金叉因子
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            score += weights['ma']; reasons.append("MA金叉")
            
        # 波動率因子
        chg = ((float(curr['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100
        if abs(chg) >= 7.0:
            score += weights['vol']; reasons.append(f"劇烈波動({round(chg,1)}%)")
            
        # 爆量因子
        if float(curr['Volume']) > df['Volume'].mean() * 2:
            score += weights['vxx']; reasons.append("爆量")

        return {
            "代碼": ticker, "總分": score, "現價": round(float(curr['Close']), 2),
            "RSI": round(float(curr['RSI']), 1), "訊號": " + ".join(reasons)
        }
    except: return None

# --- 4. 頁面導覽 ---
page = st.sidebar.radio("導覽選單", ["1. 全市場資金選股", "2. 多因子決策與持倉"])

st.sidebar.divider()
st.sidebar.header("🛠️ 權重與門檻設定")
w_rsi = st.sidebar.slider("RSI 超賣權重", 0, 100, 40)
w_ma = st.sidebar.slider("MA 金叉權重", 0, 100, 30)
w_vol = st.sidebar.slider("劇烈波動權重", 0, 100, 20)
w_vxx = st.sidebar.slider("成交爆量權重", 0, 100, 10)
buy_threshold = st.sidebar.slider("買入建議門檻 (分)", 10, 100, 30)

# --- 頁面 1：全面資金選股 ---
if page == "1. 全市場資金選股":
    st.title("🏆 全市場資金熱點監測")
    st.info("此頁面採用全面掃描模式，會從證交所獲取最新清單並計算「成交值指標」。")
    
    if st.button("🚀 開始深度掃描 (需時較長)", type="primary"):
        with st.spinner("正在獲取最新股票清單..."):
            all_list = get_full_market_tickers()
        
        res_rank = []
        p_bar = st.progress(0, text="全面計算成交值中...")
        
        batch_size = 40
        for i in range(0, len(all_list), batch_size):
            batch = all_list[i : i + batch_size]
            df = yf.download(batch, period="2d", group_by='ticker', threads=True, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        # 成交值指標計算
                        val = (float(last['Close']) * float(last['Volume'])) / 1e8
                        res_rank.append({"股票代號": t, "收盤價": float(last['Close']), "成交值(億)": val})
                except: continue
            time.sleep(random.uniform(0.1, 0.3)) # 防止被鎖 IP
            p_bar.progress(min((i + batch_size) / len(all_list), 1.0))
        
        if res_rank:
            top_100 = pd.DataFrame(res_rank).sort_values("成交值(億)", ascending=False).head(100)
            st.session_state.top_100_cache = top_100['股票代號'].tolist()
            st.subheader("🔥 今日資金最集中 Top 100")
            st.dataframe(top_100, use_container_width=True)
            st.success("✅ 掃描完成！Top 100 已鎖定，請切換至第二頁進行決策。")

# --- 頁面 2：多因子決策與持倉 ---
elif page == "2. 多因子決策與持倉":
    st.title("🤖 多因子量化決策中心")
    
    if 'top_100_cache' not in st.session_state:
        st.warning("⚠️ 請先在第一頁執行全市場掃描。")
    else:
        weights = {'rsi': w_rsi, 'ma': w_ma, 'vol': w_vol, 'vxx': w_vxx}
        final_list = []
        p_check = st.progress(0, text="計算多因子評分中...")
        
        for idx, t in enumerate(st.session_state.top_100_cache):
            res = analyze_stock(t, weights)
            if res and res['總分'] > 0:
                # 判斷動作
                is_held = t in st.session_state.portfolio and st.session_state.portfolio[t]
                if res['總分'] >= buy_threshold:
                    res['建議動作'] = "🟢 建議買入"
                elif res['RSI'] > 75 and is_held:
                    res['建議動作'] = "🔴 建議賣出"
                else:
                    res['建議動作'] = "⚪ 觀望"
                final_list.append(res)
            p_check.progress((idx + 1) / len(st.session_state.top_100_cache))

        if final_list:
            df_final = pd.DataFrame(final_list).sort_values("總分", ascending=False)
            st.dataframe(df_final, use_container_width=True)
            
            # 買賣紀錄功能
            st.divider()
            col1, col2, col3 = st.columns(3)
            with col1: t_select = st.selectbox("選擇股票", df_final['代號'])
            with col2: p_select = st.number_input("成交價格", value=0.0)
            with col3:
                if st.button("➕ 確認買入並記錄"):
                    if t_select not in st.session_state.portfolio: st.session_state.portfolio[t_select] = []
                    st.session_state.portfolio[t_select].append({"price": p_select, "date": str(datetime.now().date())})
                    save_portfolio(st.session_state.portfolio)
                    st.rerun()

    # --- 持倉管理 ---
    st.divider()
    st.subheader("💼 我的持倉紀錄")
    summary = []
    for t, trades in st.session_state.portfolio.items():
        if trades:
            avg = sum([x['price'] for x in trades]) / len(trades)
            summary.append({"代號": t, "數量": len(trades), "均價": round(avg, 2)})
    
    if summary:
        df_p = pd.DataFrame(summary)
        st.table(df_p)
        del_t = st.selectbox("選擇移除持倉", df_p['代號'])
        if st.button("🗑️ 執行清倉"):
            st.session_state.portfolio[del_t] = []
            save_portfolio(st.session_state.portfolio)
            st.rerun()
    else:
        st.info("尚無持有股票。")
