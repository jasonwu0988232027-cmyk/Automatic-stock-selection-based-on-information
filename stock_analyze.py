import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

# 關閉 SSL 驗證警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股測試版 - 快速掃描", layout="wide")

@st.cache_data(ttl=3600)
def get_test_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {'User-Agent': 'Mozilla/5.0'}
    try:
        response = requests.get(url, headers=headers, verify=False, timeout=10)
        response.encoding = 'big5'
        df = pd.read_html(response.text)[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        tickers = [f"{t.split('  ')[0]}.TW" for t in df['有價證券代號及名稱']]
        # 【測試點】：只取前 100 隻，確保快速完成
        return [t for t in tickers if len(t) == 7][:100]
    except:
        return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW"]

st.title("🧪 台股成交值 - 快速測試版")
if st.button("開始測試 (僅 100 隻)"):
    tickers = get_test_tickers()
    st.write(f"正在測試抓取 {len(tickers)} 隻股票...")
    
    # 直接批量抓取 (測試版不分批)
    data = yf.download(tickers, period="5d", group_by='ticker', silent=True)
    
    results = []
    for t in tickers:
        try:
            df_t = data[t].dropna()
            if not df_t.empty:
                row = df_t.iloc[-1]
                results.append({"股票": t, "收盤價": row['Close'], "成交金額(億)": (row['Close'] * row['Volume'])/1e8})
        except: continue
        
    if results:
        st.table(pd.DataFrame(results).sort_values("成交金額(億)", ascending=False).head(10))
        st.success("測試成功！您的環境可以正常抓取數據。")
    else:
        st.error("測試失敗，數據返回為空。")
