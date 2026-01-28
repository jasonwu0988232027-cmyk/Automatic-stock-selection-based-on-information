import streamlit as st
import yfinance as yf
import pandas as pd
import urllib3

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股測試版 - 指標優化", layout="wide")

def get_test_list():
    return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", "2881.TW", "2882.TW", "2603.TW", "3711.TW", "2412.TW"]

st.title("🧪 台股快速測試版 (10 隻股票)")
st.caption("新增：成交值指標欄位 | 格式：統一小數點後 2 位")

if st.button("執行極速掃描"):
    tickers = get_test_list()
    try:
        df = yf.download(tickers, period="5d", group_by='ticker', threads=False)
        results = []
        for t in tickers:
            t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                p, v = float(last['Close']), float(last['Volume'])
                turnover = (p * v) / 100_000_000
                
                results.append({
                    "股票代號": t,
                    "收盤價": round(p, 2),
                    "成交量(張)": int(v // 1000),
                    "成交金額(億)": round(turnover, 2),
                    "成交值指標": round(turnover, 2) # 新增指標欄位
                })
        
        if results:
            res_df = pd.DataFrame(results).sort_values("成交金額(億)", ascending=False)
            st.success("✅ 測試成功！數據已統一格式。")
            st.dataframe(res_df.style.format(subset=["收盤價", "成交金額(億)", "成交值指標"], formatter="{:.2f}"))
        else:
            st.error("❌ 抓取失敗。")
    except Exception as e:
        st.error(f"❌ 錯誤：{e}")
