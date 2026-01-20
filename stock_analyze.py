import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime
import pandas as pd

# --- 1. 頁面基本配置 ---
st.set_page_config(page_title="股市新聞 AI 助手", layout="wide")
st.title("📈 股市漲幅排行與 AI 分析")

# 側邊欄：僅輸入金鑰
st.sidebar.header("🔑 API 設置")
user_api_key = st.sidebar.text_input("在此輸入 Gemini API Key", type="password")

# --- 2. 獲取股市數據 (不需金鑰) ---
@st.cache_data(ttl=600)
def get_market_data():
    # 追蹤 10 支熱門科技股
    tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META", "AVGO", "SMCI"]
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

# 顯示表格
st.subheader("🔥 今日漲幅前 10 股票")
df_top10 = get_market_data()
st.dataframe(df_top10, use_container_width=True, hide_index=True)

st.divider()

# --- 3. AI 分析邏輯 ---
st.subheader("🤖 AI 近七天新聞分析")

if st.button("執行 AI 深度檢索"):
    if not user_api_key:
        st.error("❌ 請先在左側輸入 API Key。")
    else:
        try:
            # 配置 API
            genai.configure(api_key=user_api_key)
            
            # 【重要修正】：嘗試使用最基礎的模型名稱，這通常能解決 404 問題
            # 如果 gemini-1.5-flash 失敗，程式會自動嘗試 gemini-pro
            model_name = 'gemini-1.5-flash' 
            model = genai.GenerativeModel(model_name)
            
            for _, row in df_top10.iterrows():
                ticker = row['代碼']
                with st.expander(f"🔍 {ticker} 財經動態分析"):
                    with st.spinner(f"正在分析 {ticker}..."):
                        prompt = f"請分析股票 {ticker} 過去 7 天的重大財經新聞，並給出專業總結。請用繁體中文回答。"
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
                        
        except Exception as e:
            error_str = str(e)
            if "404" in error_str:
                st.error("❌ 依然出現 404 錯誤：請確認您的 API Key 是否已在 Google AI Studio 啟用 Gemini API。")
            elif "403" in error_str:
                st.error("❌ 403 錯誤：您的地區（或 VPN 節點）不支援此服務。")
            else:
                st.error(f"⚠️ 發生錯誤：{error_str}")

# 頁尾資訊
st.sidebar.write("---")
st.sidebar.info(f"當前時間：{datetime.now().strftime('%Y-%m-%d %H:%M')}")
