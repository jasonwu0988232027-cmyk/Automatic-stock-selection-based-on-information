import streamlit as st
import yfinance as yf
import pandas as pd

st.set_page_config(page_title="連線測試", layout="wide")
st.title("🧪 快速連線測試 (略過證交所)")

if st.button("點擊測試"):
    # 內建 5 隻指標股
    tickers = ["2330.TW", "2317.TW", "2454.TW", "2603.TW", "2881.TW"]
    try:
        data = yf.download(tickers, period="5d", group_by='ticker', threads=False)
        res = []
        for t in tickers:
            t_df = data[t].dropna() if isinstance(data.columns, pd.MultiIndex) else data.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                val = round((float(last['Close']) * float(last['Volume'])) / 1e8, 2)
                res.append({"股票代號": t, "收盤價": round(last['Close'], 2), "成交值指標": val})
        if res:
            st.success("✅ Yahoo 數據連線正常！")
            st.table(pd.DataFrame(res))
    except Exception as e:
        st.error(f"Yahoo 連線失敗: {e}")
