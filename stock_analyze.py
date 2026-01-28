import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

# --- 基礎安全與警告處理 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交值 Top 100 自動排行榜", layout="wide")

# 常數設定
COOLDOWN_SECONDS = 300 
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
    'Mozilla/5.0 (iPhone; CPU iPhone OS 17_3 like Mac OS X) AppleWebKit/605.1.15 (KHTML, like Gecko) Version/17.2 Mobile/15E148 Safari/604.1'
]

@st.cache_data(ttl=86400)
def get_all_taiwan_tickers():
    """從證交所獲取所有上市股票代碼"""
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {'User-Agent': random.choice(USER_AGENTS)}
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'big5'
        tables = pd.read_html(response.text)
        df = tables[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        raw_tickers = df['有價證券代號及名稱'].str.split("  ").str[0]
        # 過濾純數字 4 碼代號
        clean_tickers = [f"{t}.TW" for t in raw_tickers if t.isdigit() and len(t) == 4]
        return clean_tickers
    except Exception as e:
        st.warning(f"獲取清單失敗: {e}")
        return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2881.TW"]

def fetch_stock_data(tickers):
    """強化穩定性：處理 yfinance 的各種返回格式"""
    all_data = []
    batch_size = 15  # 進一步縮小批次，提高成功率
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"🚀 數據抓取進度: {i} / {len(tickers)}...")
        
        try:
            # 請求 5 天數據確保即便當日尚未開盤，也能抓到前一天的
            df = yf.download(batch, period="5d", group_by='ticker', silent=True, threads=True)
            
            for ticker in batch:
                try:
                    # 邏輯 A: 處理多股票返回的 MultiIndex
                    if isinstance(df.columns, pd.MultiIndex):
                        target_df = df[ticker].dropna()
                    else:
                        target_df = df.dropna()
                    
                    if not target_df.empty:
                        # 抓取最後一個有效的交易日數據
                        last_row = target_df.iloc[-1]
                        price = float(last_row['Close'])
                        vol = float(last_row['Volume'])
                        turnover = price * vol
                        
                        if turnover > 0:
                            all_data.append({
                                "股票代號": ticker,
                                "收盤價": round(price, 2),
                                "成交量(張)": int(vol // 1000),
                                "成交金額(億)": round(turnover / 100_000_000, 3)
                            })
                except Exception:
                    continue
        except Exception as e:
            st.write(f"批次 {i} 抓取略過")
            
        time.sleep(random.uniform(1.0, 2.5))
        progress_bar.progress(min((i + batch_size) / len(tickers), 1.0))
        
    status_text.text("✅ 資料分析完成！")
    return pd.DataFrame(all_data)

# --- Streamlit UI ---
st.title("📈 台股當日成交值排行榜")

if 'last_run' not in st.session_state:
    st.session_state.last_run = 0

now = time.time()
time_left = COOLDOWN_SECONDS - (now - st.session_state.last_run)

if st.button("🚀 開始全市場掃描 (自動過濾無效數據)", type="primary"):
    if time_left > 0:
        st.error(f"🛑 系統冷卻中，請在 {int(time_left)} 秒後再點擊。")
    else:
        st.session_state.last_run = now
        
        with st.status("正在同步證交所名單...", expanded=False):
            full_list = get_all_taiwan_tickers()
        
        # --- 效能建議：為了測試建議先取 200 隻，正式版可拿掉下行 ---
        # full_list = full_list[:200] 
        
        df_result = fetch_stock_data(full_list)
        
        if not df_result.empty:
            top_100 = df_result.sort_values(by="成交金額(億)", ascending=False).head(100).reset_index(drop=True)
            top_100.index += 1
            
            # 顯示結果區
            st.success(f"成功分析 {len(df_result)} 隻股票")
            
            col1, col2 = st.columns([2, 1])
            with col1:
                st.dataframe(top_100, height=500, use_container_width=True)
            with col2:
                st.write("🔥 成交值前 10 名比例")
                st.bar_chart(top_100.head(10).set_index("股票代號")["成交金額(億)"])

            csv_file = top_100.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載排行榜 CSV", data=csv_file, file_name="TW_Stock_Rank.csv")
        else:
            st.error("❌ 抓取結果仍為空。請檢查是否為週末（Yahoo API 有時在週日會維修）或嘗試減少掃描數量。")

st.divider()
st.caption(f"最後更新：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
