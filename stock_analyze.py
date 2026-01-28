import streamlit as st
import yfinance as yf
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股指標測試", layout="wide")

st.title("🧪 成交值指標 - 快速測試 (10 隻)")

if st.button("執行極速掃描"):
    # 預設 10 隻指標股
    tickers = ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2881.TW", "2882.TW", "2603.TW", "3711.TW", "2412.TW"]
    
    try:
        df = yf.download(tickers, period="5d", group_by='ticker', threads=False)
        results = []
        for t in tickers:
            t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                p, v = float(last['Close']), float(last['Volume'])
                indicator = round((p * v) / 100_000_000, 2)
                results.append({
                    "股票代號": t, 
                    "收盤價": round(p, 2), 
                    "成交金額(億)": indicator, 
                    "成交值指標": indicator
                })
        
        if results:
            res_df = pd.DataFrame(results).sort_values("成交值指標", ascending=False)
            st.success("✅ 測試成功！")
            # 格式化顯示
            st.dataframe(res_df.style.format({c: "{:.2f}" for c in ["收盤價", "成交金額(億)", "成交值指標"]}))
        else:
            st.error("查無數據。")
    except Exception as e:
        st.error(f"錯誤：{e}")
