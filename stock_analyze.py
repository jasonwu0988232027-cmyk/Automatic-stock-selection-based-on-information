import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

# --- 基礎安全設定 ---
# 關閉 SSL 驗證警告 (針對證交所網站)
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

# Streamlit 頁面配置
st.set_page_config(page_title="台股成交值 Top 100 自動排行榜", layout="wide")

# 常數設定
COOLDOWN_SECONDS = 300  # 兩次大掃描之間的強制冷卻時間 (5 分鐘)

# --- 1. 自動獲取台股清單 (含 SSL 錯誤修正) ---
@st.cache_data(ttl=86400)
def get_all_taiwan_tickers():
    """從證交所獲取所有上市股票代碼"""
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
    }
    
    try:
        # verify=False 解決 SSL: CERTIFICATE_VERIFY_FAILED 錯誤
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'big5'
        
        tables = pd.read_html(response.text)
        df = tables[0]
        df.columns = df.iloc[0]
        
        # 篩選代號清單 (找出有 '  ' 分隔的行，並取前 4 位為純數字者)
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        raw_tickers = df['有價證券代號及名稱'].str.split("  ").str[0]
        
        clean_tickers = [f"{t}.TW" for t in raw_tickers if t.isdigit() and len(t) == 4]
        return clean_tickers
    except Exception as e:
        st.warning(f"自動抓取清單失敗 ({e})，改用預設核心持股清單。")
        return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2881.TW", "2882.TW", "2603.TW"]

# --- 2. 批量抓取成交數據 (含防封鎖延遲) ---
def fetch_stock_data(tickers):
    """分批下載數據，降低被 Yahoo Finance 封鎖的風險"""
    all_data = []
    batch_size = 50 
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"🚀 正在分析數據: {i} / {len(tickers)} 隻股票...")
        
        try:
            # 批量抓取當日數據
            df = yf.download(batch, period="1d", group_by='ticker', silent=True, threads=True)
            
            for ticker in batch:
                if ticker in df and not df[ticker].empty:
                    last_price = df[ticker]['Close'].iloc[-1]
                    volume = df[ticker]['Volume'].iloc[-1]
                    turnover = last_price * volume # 成交值
                    
                    if not pd.isna(turnover) and turnover > 0:
                        all_data.append({
                            "股票代號": ticker,
                            "收盤價": round(last_price, 2),
                            "成交量(張)": int(volume // 1000),
                            "成交金額(億)": round(turnover / 100_000_000, 3)
                        })
        except:
            continue
            
        # 關鍵防封鎖：每組請求後隨機休息 2-4 秒
        time.sleep(random.uniform(2, 4))
        progress_bar.progress(min((i + batch_size) / len(tickers), 1.0))
        
    status_text.text("✅ 資料分析完成！")
    return pd.DataFrame(all_data)

# --- 3. Streamlit 主介面 ---
st.title("📊 台股當日成交值 Top 100")
st.info("點擊下方按鈕開始掃描全台股市場。為了保護您的 IP，每次執行後有 5 分鐘冷卻時間。")

# 初始化 Session State 記錄運行時間
if 'last_run' not in st.session_state:
    st.session_state.last_run = 0

now = time.time()
time_left = COOLDOWN_SECONDS - (now - st.session_state.last_run)

if st.button("開始自動查詢", type="primary"):
    if time_left > 0:
        st.error(f"請稍候再試！冷卻時間還剩 {int(time_left)} 秒。")
    else:
        st.session_state.last_run = now
        
        with st.status("正在執行自動化流程...", expanded=True) as status:
            st.write("🔍 正在向證交所獲取最新股票清單...")
            ticker_list = get_all_taiwan_tickers()
            st.write(f"已識別 {len(ticker_list)} 隻有效股票代碼。")
            
            st.write("⏳ 正在計算各股成交值 (含防封鎖延遲機制)...")
            final_df = fetch_stock_data(ticker_list)
            status.update(label="數據處理完畢！", state="complete", expanded=False)
        
        if not final_df.empty:
            # 排序並取前 100
            top_100 = final_df.sort_values(by="成交金額(億)", ascending=False).head(100).reset_index(drop=True)
            top_100.index += 1 # 排名從 1 開始
            
            st.subheader(f"🏆 今日成交值排行榜 (前 100 名)")
            st.dataframe(top_100, use_container_width=True)
            
            # 簡單視覺化
            st.bar_chart(data=top_100.head(10).set_index("股票代號")["成交金額(億)"])
            
            # 提供 CSV 下載
            csv_data = top_100.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載完整報表 (CSV)", data=csv_data, file_name="TW_Stock_Top100.csv", mime="text/csv")
        else:
            st.error("掃描結果為空，請檢查網路連線或稍後再試。")

st.divider()
st.caption(f"數據更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 數據源：Yahoo Finance / TWSE")
