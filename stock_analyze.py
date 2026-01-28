import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
from datetime import datetime

st.set_page_config(page_title="全台股成交值 Top 100", layout="wide")

# --- 防封鎖機制：設定冷卻時間 ---
COOLDOWN_SECONDS = 300  # 每次抓取後強制冷卻 5 分鐘 (可自行調整)

@st.cache_data(ttl=COOLDOWN_SECONDS)
def get_all_taiwan_tickers():
    """自動從證交所/櫃買中心獲取所有股票代碼"""
    # 這裡使用簡單的讀取方式，實務上可串接 API
    # 為示範效能，我們先組合常見的上市櫃區段，或建議從外部 CSV 讀入
    # 這裡以台灣前 500 大市值為例以兼顧速度與準確度
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2" # 上市股票
    tables = pd.read_html(url)
    df = tables[0]
    df.columns = df.iloc[0]
    df = df[df['有價證券代號及名稱'].str.contains("  ")] # 篩選股票
    tickers = df['有價證券代號及名稱'].str.split("  ").str[0]
    return [f"{t}.TW" for t in tickers if len(t) == 4]

@st.cache_data(show_spinner=False)
def fetch_data_with_retry(tickers):
    """分批抓取數據並加入隨機延遲"""
    all_data = []
    batch_size = 50  # 每 50 隻一組，避免單次請求過大
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"正在處理第 {i} 隻至第 {i+batch_size} 隻股票...")
        
        # 批量下載
        df = yf.download(batch, period="1d", group_by='ticker', silent=True, threads=True)
        
        for ticker in batch:
            try:
                if ticker in df and not df[ticker].empty:
                    last_price = df[ticker]['Close'].iloc[-1]
                    volume = df[ticker]['Volume'].iloc[-1]
                    turnover = last_price * volume
                    if not pd.isna(turnover):
                        all_data.append({
                            "代號": ticker,
                            "收盤價": last_price,
                            "成交量": volume,
                            "成交金額": turnover
                        })
            except:
                continue
        
        # --- CD 延遲邏輯 ---
        # 每一組後隨機休息 2~5 秒，模擬真人行為
        sleep_time = random.uniform(2, 5)
        time.sleep(sleep_time)
        
        # 更新進度條
        progress_bar.progress(min((i + batch_size) / len(tickers), 1.0))
        
    return pd.DataFrame(all_data)

# --- 主程式介面 ---
st.title("📊 全台股成交值 Top 100 自動排行榜")

# 檢查上次執行時間，實施強制冷卻
if 'last_run' not in st.session_state:
    st.session_state.last_run = 0

current_time = time.time()
time_diff = current_time - st.session_state.last_run

if st.button("🚀 開始掃描全市場 (需時約 1-2 分鐘)"):
    if time_diff < COOLDOWN_SECONDS:
        st.warning(f"⚠️ 冷卻中！為了保護 IP，請在 {int(COOLDOWN_SECONDS - time_diff)} 秒後再試。")
    else:
        st.session_state.last_run = current_time
        
        with st.status("正在獲取股票清單...", expanded=True) as status:
            ticker_list = get_all_taiwan_tickers()
            st.write(f"共找獲取 {len(ticker_list)} 隻股票代碼。")
            
            final_df = fetch_data_with_retry(ticker_list)
            status.update(label="掃描完成！", state="complete", expanded=False)
        
        if not final_df.empty:
            top_100 = final_df.sort_values(by="成交金額", ascending=False).head(100)
            
            st.subheader("🏆 今日成交值 Top 100")
            st.dataframe(
                top_100.style.format({"收盤價": "{:.2f}", "成交金額": "{:,.0f}", "成交量": "{:,.0f}"}),
                use_container_width=True
            )
        else:
            st.error("抓取失敗，可能是 API 限制或網路問題。")
