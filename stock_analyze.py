import streamlit as st
import yfinance as yf
import pandas as pd
import urllib3

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)

st.set_page_config(page_title="台股測試版", layout="wide")

def get_test_list():
    # 台灣前 10 大權值股代碼
    return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", 
            "2881.TW", "2882.TW", "2603.TW", "3711.TW", "2412.TW"]

st.title("🧪 台股快速測試版 (10 隻股票)")
st.caption("修正版：已移除不相容的 silent 參數")

if st.button("執行極速掃描"):
    tickers = get_test_list()
    st.info(f"正在掃描：{tickers}")
    
    try:
        # 移除 silent=True 以相容舊版 yfinance
        df = yf.download(tickers, period="5d", group_by='ticker', threads=False)
        
        results = []
        for t in tickers:
            # 判斷 MultiIndex 結構
            t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                price = float(last['Close'])
                volume = float(last['Volume'])
                results.append({
                    "代號": t,
                    "收盤價": round(price, 2),
                    "成交金額(億)": round((price * volume) / 100_000_000, 3)
                })
        
        if results:
            st.success("✅ 數據抓取成功！")
            st.table(pd.DataFrame(results).sort_values("成交金額(億)", ascending=False))
        else:
            st.error("❌ 抓取失敗：返回數據為空。")
    except Exception as e:
        st.error(f"❌ 發生錯誤：{e}")
