import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股成交值指標排行榜", layout="wide")

@st.cache_data(ttl=3600)
def get_all_tickers_safe():
    """強化版：模擬瀏覽器行為獲取證交所名單"""
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36',
        'Accept': 'text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8',
        'Accept-Language': 'zh-TW,zh;q=0.9,en-US;q=0.8,en;q=0.7',
        'Referer': 'https://www.google.com/'
    }
    try:
        session = requests.Session()
        response = session.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'big5'
        
        # 嘗試解析表格
        tables = pd.read_html(response.text)
        df = tables[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        
        tickers = []
        for val in df['有價證券代號及名稱']:
            code = val.split("  ")[0].strip()
            if code.isdigit() and len(code) == 4:
                tickers.append(f"{code}.TW")
        return tickers
    except Exception as e:
        st.error(f"證交所連線仍被阻擋: {e}")
        # 如果失敗，回傳最核心的 50 隻股票作為保險備案
        return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2603.TW", "2881.TW", "2882.TW"]

def fetch_data(tickers):
    all_res = []
    batch_size = 15
    p_bar = st.progress(0)
    status = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status.text(f"⏳ 正在掃描成交值指標: {i} / {len(tickers)}...")
        try:
            df = yf.download(batch, period="5d", group_by='ticker', threads=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        p, v = float(last['Close']), float(last['Volume'])
                        val = round((p * v) / 100_000_000, 2)
                        if val > 0:
                            all_res.append({
                                "股票代號": t, 
                                "收盤價": round(p, 2), 
                                "成交量(張)": int(v // 1000), 
                                "成交金額(億)": val, 
                                "成交值指標": val
                            })
                except: continue
        except: pass
        time.sleep(random.uniform(1.0, 2.0))
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    status.empty()
    return pd.DataFrame(all_res)

# --- UI ---
st.title("📊 台股成交值指標 Top 100")

if st.button("🚀 執行全市場掃描", type="primary"):
    with st.spinner("正在安全獲取證交所名單..."):
        all_list = get_all_tickers_safe()
    
    if len(all_list) > 10:
        df_raw = fetch_data(all_list)
        if not df_raw.empty:
            # 依指標排序取前 100
            top_100 = df_raw.sort_values("成交值指標", ascending=False).head(100).reset_index(drop=True)
            top_100.index += 1
            
            st.subheader(f"🏆 資金熱點 Top 100 ({datetime.now().strftime('%Y-%m-%d')})")
            
            # 強制兩位小數並上色
            try:
                styled = top_100.style.format({c: "{:.2f}" for c in ["收盤價", "成交金額(億)", "成交值指標"]})\
                                       .background_gradient(subset=['成交值指標'], cmap='YlOrRd')
                st.dataframe(styled, use_container_width=True)
            except:
                st.dataframe(top_100, use_container_width=True)
            
            st.download_button("📥 下載 CSV", data=top_100.to_csv(index=False).encode('utf-8-sig'), file_name="Top100.csv")
        else:
            st.error("Yahoo 數據抓取失敗。")
    else:
        st.error("無法取得名單，請稍後再試。")
