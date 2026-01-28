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
st.set_page_config(page_title="台股全面掃描交易系統", layout="wide")

DB_FILE = "portfolio.json"

# 持倉管理
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

# --- 1. 全面獲取股票代碼 (您的原始全面模式) ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    """從證交所獲取最完整清單"""
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
    
    # 強力保險：內嵌基礎清單以防爬蟲失敗
    return [f"{i:04d}.TW" for i in range(1101, 9999)]

# --- 2. 多因子分析邏輯 (整合自您的權重系統) ---
def analyze_stock(ticker, weights):
    """計算多個技術因子得分"""
    try:
        df = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)

        curr, prev = df.iloc[-1], df.iloc[-2]
        score = 0
        reasons = []

        if float(curr['RSI']) < 30: 
            score += weights['rsi']; reasons.append("RSI超賣")
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            score += weights['ma']; reasons.append("MA金叉")
        chg = ((float(curr['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100
        if abs(chg) >= 7.0:
            score += weights['vol']; reasons.append(f"劇烈波動({round(chg,1)}%)")
        if float(curr['Volume']) > df['Volume'].mean() * 2:
            score += weights['vxx']; reasons.append("爆量")

        return {
            "代碼": ticker, "總分": score, "現價": round(float(curr['Close']), 2),
            "RSI": round(float(curr['RSI']), 1), "訊號": " + ".join(reasons)
        }
    except: return None

# --- UI 導航 ---
page = st.sidebar.radio("功能選單", ["1. 全市場資金選股", "2. 多因子決策與持倉"])

st.sidebar.divider()
st.sidebar.header("⚙️ 因子權重分配")
w_rsi = st.sidebar.slider("RSI 超賣權重", 0, 100, 40)
w_ma = st.sidebar.slider("MA 金叉權重", 0, 100, 30)
w_vol = st.sidebar.slider("劇烈波動權重", 0, 100, 20)
w_vxx = st.sidebar.slider("成交爆量權重", 0, 100, 10)
buy_threshold = st.sidebar.slider("買入門檻", 10, 100, 30)

# --- 頁面 1：全市場掃描 (解決卡死關鍵) ---
if page == "1. 全市場資金選股":
    st.title("🏆 全市場資金指標排行")
    
    if st.button("🚀 啟動全市場深度掃描"):
        all_list = get_full_market_tickers()
        res_rank = []
        p_bar = st.progress(0, text="正在分批獲取數據...")
        
        # 使用更大的 Batch Size 並增加等待時間，避免被 Yahoo 封鎖
        batch_size = 50 
        for i in range(0, len(all_list), batch_size):
            batch = all_list[i : i + batch_size]
            try:
                # 關鍵優化：增加 threads=True 提高速度，下載失敗不中斷程式
                data = yf.download(batch, period="2d", group_by='ticker', threads=True, progress=False)
                for t in batch:
                    try:
                        t_df = data[t].dropna() if isinstance(data.columns, pd.MultiIndex) else data.dropna()
                        if not t_df.empty:
                            last = t_df.iloc[-1]
                            val = (float(last['Close']) * float(last['Volume'])) / 1e8
                            res_rank.append({"股票代號": t, "收盤價": float(last['Close']), "成交值指標(億)": val})
                    except: continue
            except: pass
            
            p_bar.progress(min((i + batch_size) / len(all_list), 1.0))
            time.sleep(random.uniform(0.5, 1.0)) # 強制延遲，避免卡死
        
        if res_rank:
            top_100 = pd.DataFrame(res_rank).sort_values("成交值指標(億)", ascending=False).head(100)
            st.session_state.top_100_list = top_100['股票代號'].tolist()
            st.dataframe(top_100, use_container_width=True)
            st.success("✅ 掃描完成！Top 100 已存入，請至下一頁查看。")

# --- 頁面 2：交易決策 ---
elif page == "2. 多因子決策與持倉":
    st.title("🤖 交易決策中心")
    if 'top_100_list' not in st.session_state:
        st.warning("請先執行第一頁的選股掃描。")
    else:
        weights = {'rsi': w_rsi, 'ma': w_ma, 'vol': w_vol, 'vxx': w_vxx}
        signals = []
        p_check = st.progress(0, text="計算評分中...")
        
        for idx, t in enumerate(st.session_state.top_100_list):
            res = analyze_stock(t, weights)
            if res and res['總分'] > 0:
                is_held = t in st.session_state.portfolio and st.session_state.portfolio[t]
                if res['總分'] >= buy_threshold:
                    res['建議動作'] = "🟢 買入建議"
                elif res['RSI'] > 75 and is_held:
                    res['建議動作'] = "🔴 賣出建議"
                else:
                    res['建議動作'] = "觀望"
                signals.append(res)
            p_check.progress((idx + 1) / 100)
        
        if signals:
            st.dataframe(pd.DataFrame(signals).sort_values("總分", ascending=False), use_container_width=True)
            
            # 手動記錄買入
            st.divider()
            c1, c2 = st.columns(2)
            with c1: t_in = st.selectbox("選股代號", [s['代碼'] for s in signals])
            with c2: p_in = st.number_input("價格", value=0.0)
            if st.button("➕ 加入持倉"):
                if t_in not in st.session_state.portfolio: st.session_state.portfolio[t_in] = []
                st.session_state.portfolio[t_in].append({"price": p_in, "date": str(datetime.now().date())})
                save_portfolio(st.session_state.portfolio)
                st.rerun()

    # --- 持倉管理 ---
    st.divider()
    st.subheader("💼 我的持倉")
    p_data = [{"代號": k, "張數": len(v), "成本": round(sum([i['price'] for i in v])/len(v), 2)} 
              for k, v in st.session_state.portfolio.items() if v]
    if p_data:
        st.table(pd.DataFrame(p_data))
        t_del = st.selectbox("選擇移除", [d['代號'] for d in p_data])
        if st.button("🗑️ 移除標的"):
            st.session_state.portfolio[t_del] = []
            save_portfolio(st.session_state.portfolio)
            st.rerun()
