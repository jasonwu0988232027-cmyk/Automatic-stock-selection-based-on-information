import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime
import pandas as pd

# --- 1. 頁面基本配置 ---
st.set_page_config(page_title="股市新聞 AI 助手", layout="wide")
st.title("📈 股市熱門股分析 (直接模式)")

# 側邊欄僅供輸入，不進行強制連線驗證
st.sidebar.header("🔑 API 設置")
user_api_key = st.sidebar.text_input("在此輸入 Gemini API Key", type="password")

# 顯示當前時間
now = datetime.now()
st.sidebar.info(f"📅 系統時間：{now.strftime('%Y-%m-%d %H:%M')}")

# --- 2. 股市數據抓取 (無需 API Key) ---
@st.cache_data(ttl=300)
def get_market_data():
    # 預設追蹤的熱門標的
    tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AVGO"]
    data = []
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                price = hist['Close'].iloc[-1]
                change = (price - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100
                data.append({"代碼": t, "現價": round(price, 2), "漲幅%": round(change, 2)})
        except: continue
    return pd.DataFrame(data).sort_values("漲幅%", ascending=False).head(10)

# --- 3. UI 主畫面 ---

# 無論有無 Key，優先顯示股市數據
st.subheader("🔥 今日漲幅前 10 股票")
df_top10 = get_market_data()
st.dataframe(df_top10, use_container_width=True, hide_index=True)

st.divider()

# --- 4. AI 分析邏輯 (僅在點擊按鈕時執行) ---
st.subheader("🤖 AI 近七天新聞分析")

if st.button("執行 AI 深度檢索"):
    if not user_api_key:
        st.error("❌ 請先在左側輸入 API Key 才能執行 AI 分析。")
    else:
        try:
            # 配置並直接建立模型
            genai.configure(api_key=user_api_key)
            model = genai.GenerativeModel('gemini-1.5-flash-latest')
            
            for _, row in df_top10.iterrows():
                ticker = row['代碼']
                with st.expander(f"🔍 {ticker} 財經動態分析"):
                    with st.spinner(f"正在分析 {ticker}..."):
                        prompt = f"分析股票 {ticker} 過去 7 天的重大財經新聞，並給出專業總結。請用繁體中文。"
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
        except Exception as e:
            st.error(f"⚠️ AI 執行過程中出錯：{str(e)}")
            st.info("提示：如果出現 403 錯誤，通常是地區限制；401 則是金鑰輸入錯誤。")
