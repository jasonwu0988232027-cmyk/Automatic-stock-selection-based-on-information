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
st.caption("結果將重點顯示【成交金額(億)】")

if st.button("執行極速掃描"):
    tickers = get_test_list()
    st.info(f"正在掃描：{tickers}")
    
    try:
        # 下載數據 (移除 silent 以確保相容性)
        df = yf.download(tickers, period="5d", group_by='ticker', threads=False)
        
        results = []
        for t in tickers:
            t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
            if not t_df.empty:
                last = t_df.iloc[-1]
                price = float(last['Close'])
                volume = float(last['Volume'])
                turnover_billion = (price * volume) / 100_000_000 # 計算成交值
                
                results.append({
                    "股票代號": t,
                    "當前股價": round(price, 2),
                    "成交金額(億)": round(turnover_billion, 3)
                })
        
        if results:
            st.success("✅ 測試成功！資料如下：")
            res_df = pd.DataFrame(results).sort_values("成交金額(億)", ascending=False)
            st.table(res_df) # 使用表格直接呈現關鍵數據
        else:
            st.error("❌ 抓取失敗：數據返回為空。")
    except Exception as e:
        st.error(f"❌ 發生錯誤：{e}")
