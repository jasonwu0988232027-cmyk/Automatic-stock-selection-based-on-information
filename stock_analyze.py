import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股排行榜-完整版", layout="wide")

@st.cache_data(ttl=86400)
def get_all_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=15)
        res.encoding = 'big5'
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        return [f"{t.split('  ')[0]}.TW" for t in df['有價證券代號及名稱'] if len(t.split('  ')[0]) == 4]
    except: return ["2330.TW", "2317.TW", "2454.TW"]

def fetch_data(tickers):
    all_res = []
    batch_size = 15
    p_bar = st.progress(0)
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        try:
            df = yf.download(batch, period="5d", group_by='ticker', threads=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        p, v = float(last['Close']), float(last['Volume'])
                        turnover = round((p * v) / 100_000_000, 2)
                        if turnover > 0:
                            all_res.append({"股票代號": t, "收盤價": round(p, 2), "成交量(張)": int(v // 1000), "成交金額(億)": turnover, "成交值指標": turnover})
                except: continue
        except: pass
        time.sleep(random.uniform(1.0, 2.0))
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    return pd.DataFrame(all_res)

st.title("📊 台股成交值 Top 100 指標排行榜")
if st.button("🚀 開始分析全市場"):
    tickers = get_all_tickers()
    df_final = fetch_data(tickers)
    if not df_final.empty:
        top_100 = df_final.sort_values("成交金額(億)", ascending=False).head(100).reset_index(drop=True)
        top_100.index += 1
        try:
            # 統一兩位小數並上色
            styled = top_100.style.format({c: "{:.2f}" for c in ["收盤價", "成交金額(億)", "成交值指標"]}).background_gradient(subset=['成交值指標'], cmap='Oranges')
            st.dataframe(styled, use_container_width=True)
        except:
            st.dataframe(top_100, use_container_width=True)
        st.download_button("📥 下載 CSV", data=top_100.to_csv(index=False).encode('utf-8-sig'), file_name="Rank.csv")
