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
st.set_page_config(page_title="台股全市場排行榜 - 穩定版", layout="wide")

@st.cache_data(ttl=86400)
def get_all_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) Chrome/121.0.0.0'}
    try:
        res = requests.get(url, headers=headers, verify=False, timeout=15)
        res.encoding = 'big5'
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        return [f"{t.split('  ')[0]}.TW" for t in df['有價證券代號及名稱'] if len(t.split('  ')[0]) == 4]
    except:
        return ["2330.TW", "2317.TW", "2454.TW"]

def fetch_data_full(tickers):
    final_results = []
    batch_size = 15 
    p_bar = st.progress(0)
    status = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status.text(f"⏳ 正在分析市場資金流: {i} / {len(tickers)}...")
        try:
            df = yf.download(batch, period="5d", group_by='ticker', threads=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        p, v = float(last['Close']), float(last['Volume'])
                        turnover = (p * v) / 100_000_000
                        if turnover > 0:
                            final_results.append({
                                "股票代號": t,
                                "收盤價": round(p, 2),
                                "成交量(張)": int(v // 1000),
                                "成交金額(億)": round(turnover, 2),
                                "成交值指標": round(turnover, 2)
                            })
                except: continue
        except: pass
        time.sleep(random.uniform(1.0, 2.0))
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    status.text("✅ 數據掃描完成")
    return pd.DataFrame(final_results)

# --- 主 UI ---
st.title("📊 台股成交值 Top 100 指標排行榜")

if 'last_run' not in st.session_state: st.session_state.last_run = 0
time_diff = time.time() - st.session_state.last_run

if st.button("🚀 開始分析全市場指標", type="primary"):
    if time_diff < 300:
        st.error(f"🛑 系統冷卻中，請等待 {int(300 - time_diff)} 秒。")
    else:
        st.session_state.last_run = time.time()
        tickers = get_all_tickers()
        st.write(f"🔍 搜尋到 {len(tickers)} 隻股票，計算中...")
        
        df_final = fetch_data_full(tickers)
        
        if not df_final.empty:
            top_100 = df_final.sort_values("成交金額(億)", ascending=False).head(100).reset_index(drop=True)
            top_100.index += 1
            
            st.subheader("🏆 今日成交值 Top 100")
            
            # --- 安全顯示邏輯 ---
            try:
                # 嘗試使用帶顏色的樣式
                styled_df = top_100.style.format({
                    "收盤價": "{:.2f}",
                    "成交金額(億)": "{:.2f}",
                    "成交值指標": "{:.2f}"
                }).background_gradient(subset=['成交值指標'], cmap='Oranges')
                st.dataframe(styled_df, use_container_width=True)
            except ImportError:
                # 如果缺少 matplotlib，則顯示普通表格
                st.warning("提示：安裝 matplotlib 可啟用表格顏色漸層。")
                st.dataframe(top_100, use_container_width=True)
            
            csv = top_100.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載此報表 (CSV)", data=csv, file_name="Stock_Indicator_Rank.csv")
        else:
            st.error("掃描結果為空。")
