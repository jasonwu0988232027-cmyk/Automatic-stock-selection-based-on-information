import streamlit as st
import yfinance as yf
import pandas as pd
import requests
import urllib3
import time

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股測試版", layout="wide")

def get_test_list():
    # 直接定義台灣前 10 大權值股，略過網頁抓取清單步驟以求極速
    return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", 
            "2881.TW", "2882.TW", "2603.TW", "3711.TW", "2412.TW"]

st.title("🧪 台股快速測試版 (10 隻股票)")

if st.button("執行極速掃描"):
    tickers = get_test_list()
    st.info(f"正在掃描：{tickers}")
    
    try:
        # 使用 threads=False 提高穩定性
        df = yf.download(tickers, period="5d", group_by='ticker', silent=True, threads=False)
        
        results = []
        for t in tickers:
            t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                results.append({
                    "代號": t,
                    "收盤價": last['Close'],
                    "成交金額(億)": (last['Close'] * last['Volume']) / 1e8
                })
        
        if results:
            st.success("✅ 數據抓取成功！")
            st.table(pd.DataFrame(results).sort_values("成交金額(億)", ascending=False))
        else:
            st.error("❌ 抓取失敗：返回數據為空。")
    except Exception as e:
        st.error(f"❌ 發生錯誤：{e}")
