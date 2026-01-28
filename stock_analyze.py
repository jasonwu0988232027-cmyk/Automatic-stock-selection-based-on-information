import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
from datetime import datetime

# --- 頁面基本設定 ---
st.set_page_config(page_title="台股成交值自動排行榜", layout="wide")

# --- 設定常數 ---
COOLDOWN_SECONDS = 300  # 強制冷卻時間 (5分鐘)

# --- 1. 自動獲取台股代碼 (解決 URLError) ---
@st.cache_data(ttl=86400) # 股票名單一天更新一次即可
def get_all_taiwan_tickers():
    """從證交所獲取所有上市股票代碼，並偽裝瀏覽器標頭"""
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # 使用 requests 抓取並指定編碼
        response = requests.get(url, headers=headers, timeout=15)
        response.encoding = 'big5'
        
        # 解析 HTML
        tables = pd.read_html(response.text)
        df = tables[0]
        df.columns = df.iloc[0]
        
        # 篩選標準股票代號 (排除權證、ETF等，僅保留 4 位數代碼)
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        raw_tickers = df['有價證券代號及名稱'].str.split("  ").str[0]
        
        # 過濾出純數字且長度為 4 的代號
        clean_tickers = [f"{t}.TW" for t in raw_tickers if t.isdigit() and len(t) == 4]
        return clean_tickers
    except Exception as e:
        st.error(f"獲取股票名單時出錯: {e}")
        return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW"] # 保底清單

# --- 2. 批量抓取數據 (含 CD 與 隨機延遲) ---
def fetch_stock_data(tickers):
    """分組抓取數據以避免 IP 封鎖"""
    all_results = []
    batch_size = 50 
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"🚀 正在分析市場數據 ({i}/{len(tickers)})...")
        
        # 使用 yfinance 批量下載
        try:
            df = yf.download(batch, period="1d", group_by='ticker', silent=True, threads=True)
            
            for ticker in batch:
                if ticker in df and not df[ticker].empty:
                    # 抓取最後一筆成交價與成交量
                    last_price = df[ticker]['Close'].iloc[-1]
                    volume = df[ticker]['Volume'].iloc[-1]
                    turnover = last_price * volume
                    
                    if not pd.isna(turnover) and turnover > 0:
                        all_results.append({
                            "股票代號": ticker,
                            "收盤價": round(last_price, 2),
                            "成交量(張)": int(volume // 1000), # 換算為張數
                            "成交金額(億)": round(turnover / 100_000_000, 2)
                        })
        except Exception:
            continue
            
        # --- 防封鎖 CD ---
        time.sleep(random.uniform(2, 4)) # 每組請求後隨機休息
        progress_bar.progress(min((i + batch_size) / len(tickers), 1.0))
        
    status_text.text("✅ 掃描完成！")
    return pd.DataFrame(all_results)

# --- 3. Streamlit UI 邏輯 ---
st.title("📈 今日台股成交值 Top 100 排行榜")
st.markdown("此工具會自動掃描全台股市場，計算各股成交總額 ($股價 \times 成交量$)。")

# 初始化 Session State
if 'last_execution_time' not in st.session_state:
    st.session_state.last_execution_time = 0

current_now = time.time()
cd_remaining = COOLDOWN_SECONDS - (current_now - st.session_state.last_execution_time)

if st.button("開始自動查找 (預計需 1-2 分鐘)"):
    if cd_remaining > 0:
        st.warning(f"⚠️ 請求過於頻繁！請等待 {int(cd_remaining)} 秒後再點擊，以防 IP 被封鎖。")
    else:
        st.session_state.last_execution_time = current_now
        
        tickers = get_all_taiwan_tickers()
        st.info(f"搜尋到 {len(tickers)} 隻上市股票，開始計算成交值...")
        
        data_df = fetch_stock_data(tickers)
        
        if not data_df.empty:
            # 排序取前 100
            top_100 = data_df.sort_values(by="成交金額(億)", ascending=False).head(100).reset_index(drop=True)
            
            # 顯示結果
            st.subheader(f"🏆 今日成交值前 100 名 ({datetime.now().strftime('%Y-%m-%d')})")
            st.dataframe(top_100, use_container_width=True)
            
            # 下載按鈕
            csv = top_100.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", data=csv, file_name="top_100_stocks.csv", mime="text/csv")
        else:
            st.error("無法獲取數據，請稍後再試。")

st.divider()
st.caption("註：成交金額為估計值。數據來源：Yahoo Finance & TWSE。")
