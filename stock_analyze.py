import streamlit as st
import yfinance as yf
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="快速測試", layout="wide")

st.title("🧪 極速連線測試")

if st.button("點擊測試連線"):
    # 只測 5 隻最不容易出錯的股票
    test_tickers = ["2330.TW", "2317.TW", "2454.TW", "2603.TW", "2881.TW"]
    try:
        data = yf.download(test_tickers, period="5d", group_by='ticker', threads=False)
        res = []
        for t in test_tickers:
            t_df = data[t].dropna() if isinstance(data.columns, pd.MultiIndex) else data.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                p, v = float(last['Close']), float(last['Volume'])
                val = round((p * v) / 100_000_000, 2)
                res.append({"股票代號": t, "收盤價": round(p, 2), "成交值指標": val})
        
        if res:
            st.success("✅ 連線正常！")
            st.table(pd.DataFrame(res))
        else:
            st.error("❌ 數據返回為空，請檢查 Yahoo Finance 是否封鎖您的 IP。")
    except Exception as e:
        st.error(f"❌ 發生錯誤: {e}")
