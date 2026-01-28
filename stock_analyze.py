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

# --- 基礎安全設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股全市場自動交易系統 (RSI-7)", layout="wide")

DB_FILE = "portfolio.json"

# --- 1. 持倉管理功能 (JSON) ---
def load_portfolio():
    if os.path.exists(DB_FILE):
        try:
            with open(DB_FILE, "r") as f: return json.load(f)
        except: return {}
    return {}

def save_portfolio(data):
    with open(DB_FILE, "w") as f: json.dump(data, f, indent=4)

# --- 2. 側邊欄：動態參數設定 ---
st.sidebar.header("⚙️ 策略參數中心")
rsi_p = st.sidebar.slider("RSI 計算週期", 3, 14, 7) # 用戶要求預設 7
buy_rsi = st.sidebar.slider("買入門檻 (RSI 低於)", 10, 40, 20)
sell_rsi = st.sidebar.slider("止盈門檻 (RSI 高於)", 60, 95, 80)
sl_pct = st.sidebar.slider("硬止損比例 (%)", 5, 20, 10) / 100

# --- 3. 交易核心邏輯 ---
def check_trade_logic(ticker, price, rsi, portfolio):
    if rsi is None or pd.isna(rsi): return "HOLD", "指標無數據"
    
    rsi_val = float(rsi)
    trades = portfolio.get(ticker, [])
    avg_cost = sum([float(t['price']) for t in trades]) / len(trades) if trades else 0
    
    # 買進訊號
    if rsi_val < buy_rsi and len(trades) < 5:
        return "BUY", f"RSI-{rsi_p} 超跌 ({rsi_val:.1f})"
    
    # 賣出訊號
    if trades:
        if price < avg_cost * (1 - sl_pct):
            return "SELL_ALL", f"觸發 {int(sl_pct*100)}% 止損"
        if rsi_val > sell_rsi:
            return "SELL_ALL", f"RSI-{rsi_p} 過熱 ({rsi_val:.1f})"
            
    return "HOLD", "觀望"

# --- 4. 選股模組 (延用 1000 隻核心清單) ---
@st.cache_data(ttl=86400)
def get_full_market_tickers():
    base_codes = [
        "1101", "1102", "1216", "1301", "1303", "1319", "1326", "1402", "1434", "1476", "1477", "1503", "1504", "1513", "1519", "1590", "1605", "1608", "1609", "1707", "1717", "1722", "1723", "1795", "1802", "1904", "2002", "2006", "2014", "2027", "2031", "2101", "2105", "2201", "2204", "2206", "2301", "2303", "2308", "2313", "2317", "2324", "2327", "2330", "2337", "2344", "2345", "2347", "2351", "2352", "2353", "2354", "2356", "2357", "2360", "2368", "2371", "2376", "2377", "2379", "2382", "2383", "2385", "2393", "2395", "2401", "2408", "2409", "2412", "2421", "2449", "2451", "2454", "2457", "2458", "2474", "2480", "2492", "2498", "2542", "2603", "2606", "2609", "2610", "2615", "2618", "2633", "2634", "2637", "2707", "2801", "2809", "2812", "2834", "2880", "2881", "2882", "2883", "2884", "2885", "2886", "2887", "2888", "2889", "2890", "2891", "2892", "2903", "2912", "3006", "3008", "3017", "3023", "3034", "3035", "3037", "3044", "3045", "3189", "3231", "3406", "3443", "3481", "3532", "3533", "3583", "3653", "3661", "3702", "3711", "3714", "4915", "4919", "4938", "4958", "4961", "4967", "5269", "5434", "5871", "5876", "5880", "6005", "6176", "6213", "6239", "6285", "6409", "6415", "6446", "6505", "6515", "6669", "6719", "6770", "8046", "8069", "8081", "8454", "8464", "9904", "9910", "9921", "9945"
    ]
    extended_list = [f"{str(i).zfill(4)}.TW" for i in range(1101, 9999)]
    return [t for t in extended_list if t.split('.')[0] in base_codes or int(t.split('.')[0]) < 3000]

# --- 5. 主程式 ---
st.title("📈 台股全市場量化交易監控系統")

if 'portfolio' not in st.session_state:
    st.session_state.portfolio = load_portfolio()

# 持倉顯示區
with st.expander("💼 持倉紀錄 (來自 portfolio.json)", expanded=True):
    p_data = [{"股票": k, "批數": len(v), "平均成本": round(sum([x['price'] for x in v])/len(v), 2)} 
              for k, v in st.session_state.portfolio.items() if v]
    if p_data:
        st.dataframe(pd.DataFrame(p_data), use_container_width=True)
    else:
        st.info("目前無任何持倉部位。")

if st.button("🚀 啟動深度掃描", type="primary"):
    all_list = get_full_market_tickers()
    
    # 第一階段：成交值排名
    res_rank = []
    p1 = st.progress(0, text="第一階段：獲取全市場成交值...")
    batch_size = 30
    for i in range(0, len(all_list), batch_size):
        batch = all_list[i:i+batch_size]
        try:
            df = yf.download(batch, period="2d", group_by='ticker', threads=True, progress=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        val = (float(last['Close']) * float(last['Volume'])) / 1e8
                        res_rank.append({"ticker": t, "price": float(last['Close']), "val": val})
                except: continue
        except: pass
        p1.progress(min((i+batch_size)/len(all_list), 1.0))
    
    if res_rank:
        top_100 = pd.DataFrame(res_rank).sort_values("val", ascending=False).head(100)
        
        # 第二階段：監視面板與 RSI 檢查
        st.subheader(f"📡 Top 10 熱門股 RSI-{rsi_p} 實時監視面板")
        m_cols = st.columns(5)
        
        final_results = []
        p2 = st.progress(0, text="第二階段：分析技術指標訊號...")
        
        for idx, row in enumerate(top_100.itertuples()):
            ticker = row.ticker
            try:
                hist = yf.download(ticker, period="1mo", interval="1d", progress=False)
                if len(hist) < rsi_p + 2: continue
                
                hist['RSI'] = ta.rsi(hist['Close'], length=rsi_p)
                curr_p = float(hist['Close'].iloc[-1])
                curr_rsi = hist['RSI'].iloc[-1]
                
                # 安全顯示面板 (防止 NaN 崩潰)
                if idx < 10:
                    with m_cols[idx % 5]:
                        rsi_str = f"{curr_rsi:.1f}" if pd.notna(curr_rsi) else "N/A"
                        st.metric(
                            label=ticker, 
                            value=f"{curr_p:.1f}", 
                            delta=f"RSI: {rsi_str}",
                            delta_color="inverse" if pd.notna(curr_rsi) and curr_rsi > sell_rsi else "normal"
                        )

                # 策略判斷
                action, reason = check_trade_logic(ticker, curr_p, curr_rsi, st.session_state.portfolio)
                if action != "HOLD":
                    final_results.append({
                        "股票代號": ticker, "動作": action, "原因": reason, 
                        "目前價格": round(curr_p, 2), f"RSI-{rsi_p}": round(curr_rsi, 1) if pd.notna(curr_rsi) else "N/A"
                    })
                    # 更新持倉
                    if action == "BUY":
                        if ticker not in st.session_state.portfolio: st.session_state.portfolio[ticker] = []
                        st.session_state.portfolio[ticker].append({"price": curr_p, "date": str(datetime.now().date())})
                    elif action == "SELL_ALL":
                        st.session_state.portfolio[ticker] = []
            except: continue
            p2.progress((idx+1)/100)
            
        save_portfolio(st.session_state.portfolio)
        
        if final_results:
            st.subheader("🚩 今日觸發買賣訊號建議")
            st.dataframe(pd.DataFrame(final_results), use_container_width=True)
        else:
            st.success(f"🏁 掃描完畢。今日 Top 100 資金熱點標的中，無標的符合您的參數條件。")
    else:
        st.error("❌ 無法獲取市場數據，請檢查網路。")
