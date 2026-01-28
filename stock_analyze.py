import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

# --- 基礎安全設定 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股成交值 Top 100 自動排行榜", layout="wide")

# 常數設定
COOLDOWN_SECONDS = 300 

# 模擬多個瀏覽器標頭，降低被封鎖機率
USER_AGENTS = [
    'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36',
    'Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/119.0.0.0 Safari/537.36',
    'Mozilla/5.0 (X11; Linux x86_64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36'
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
        clean_tickers = [f"{t}.TW" for t in raw_tickers if t.isdigit() and len(t) == 4]
        return clean_tickers
    except Exception as e:
        st.warning(f"獲取清單失敗: {e}")
        return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2881.TW"]

def fetch_stock_data(tickers):
    """強化版數據抓取：縮小 Batch 並增加錯誤跳過機制"""
    all_data = []
    # 縮小 Batch 規模至 20，這對穩定性非常有幫助
    batch_size = 20 
    
    progress_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"🚀 正在分析數據: {i} / {len(tickers)} 隻股票...")
        
        try:
            # 加入 threads=False 有時在雲端環境反而更穩定
            df = yf.download(
                batch, 
                period="1d", 
                group_by='ticker', 
                silent=True, 
                threads=True,
                timeout=20
            )
            
            for ticker in batch:
                try:
                    # 判斷多個股票返回的 DataFrame 結構
                    target_df = df[ticker] if len(batch) > 1 else df
                    
                    if not target_df.empty and 'Close' in target_df:
                        last_price = target_df['Close'].iloc[-1]
                        volume = target_df['Volume'].iloc[-1]
                        turnover = last_price * volume
                        
                        if not pd.isna(turnover) and turnover > 0:
                            all_data.append({
                                "股票代號": ticker,
                                "收盤價": round(float(last_price), 2),
                                "成交量(張)": int(volume // 1000),
                                "成交金額(億)": round(float(turnover / 100_000_000), 3)
                            })
                except:
                    continue
        except Exception as e:
            # 如果整組失敗，略過並繼續下一組
            continue
            
        # 增加延遲時間確保不被封鎖
        time.sleep(random.uniform(1.5, 3.0))
        progress_bar.progress(min((i + batch_size) / len(tickers), 1.0))
        
    status_text.text("✅ 資料分析完成！")
    return pd.DataFrame(all_data)

# --- 主介面 ---
st.title("📊 台股當日成交值 Top 100")

if 'last_run' not in st.session_state:
    st.session_state.last_run = 0

now = time.time()
time_left = COOLDOWN_SECONDS - (now - st.session_state.last_run)

if st.button("開始自動查詢", type="primary"):
    if time_left > 0:
        st.error(f"請稍候再試！冷卻時間還剩 {int(time_left)} 秒。")
    else:
        st.session_state.last_run = now
        ticker_list = get_all_taiwan_tickers()
        
        # 初次篩選：為了測試穩定性，可以先取前 300 隻（成交量通常集中在前端）
        # 如果要全掃描，請註解掉下面這行
        # ticker_list = ticker_list[:300] 
        
        final_df = fetch_stock_data(ticker_list)
        
        if not final_df.empty:
            top_100 = final_df.sort_values(by="成交金額(億)", ascending=False).head(100).reset_index(drop=True)
            top_100.index += 1
            
            st.subheader(f"🏆 今日成交值排行榜 (前 100 名)")
            st.dataframe(top_100, use_container_width=True)
            
            st.bar_chart(data=top_100.head(10).set_index("股票代號")["成交金額(億)"])
            
            csv_data = top_100.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載完整報表 (CSV)", data=csv_data, file_name="TW_Stock_Top100.csv", mime="text/csv")
        else:
            st.error("❌ 掃描結果為空。原因可能是：1.目前非開盤時間且無昨日數據 2.Yahoo Finance 暫時限制您的 IP。請等待冷卻時間結束後再試。")

st.divider()
st.caption(f"數據更新時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | 數據源：Yahoo Finance / TWSE")
