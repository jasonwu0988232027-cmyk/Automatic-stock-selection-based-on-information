import streamlit as st
import yfinance as yf
import pandas as pd
import urllib3

# 關閉 SSL 警告
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股測試版", layout="wide")

def get_test_list():
    return ["2330.TW", "2317.TW", "2454.TW", "2308.TW", "2382.TW", 
            "2881.TW", "2882.TW", "2603.TW", "3711.TW", "2412.TW"]

st.title("🧪 台股快速測試版 (10 隻股票)")
st.caption("目標：快速驗證「成交值」欄位顯示")

if st.button("執行極速掃描"):
    tickers = get_test_list()
    st.info(f"正在掃描：{tickers}")
    
    try:
        # 下載數據
        df = yf.download(tickers, period="5d", group_by='ticker', threads=False)
        
        results = []
        for t in tickers:
            t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                price = float(last['Close'])
                vol = float(last['Volume'])
                # 成交值計算
                turnover = (price * vol) / 100_000_000
                
                results.append({
                    "股票代號": t,
                    "收盤價": round(price, 2),
                    "成交量(張)": int(vol // 1000),
                    "成交金額(億)": round(turnover, 3)
                })
        
        if results:
            st.success("✅ 測試成功！")
            st.table(pd.DataFrame(results).sort_values("成交金額(億)", ascending=False))
        else:
            st.error("❌ 抓取失敗：返回數據為空。")
    except Exception as e:
        st.error(f"❌ 發生錯誤：{e}")
        
