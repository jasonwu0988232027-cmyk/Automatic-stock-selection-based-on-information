import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime
import pandas as pd

# --- 1. 頁面配置 ---
st.set_page_config(page_title="AI 股市新聞分析", layout="wide")
st.title("📈 股市漲幅排行與 Gemini AI 分析")

# --- 2. 側邊欄設置 ---
st.sidebar.header("🔑 API 設置")
user_api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password")
st.sidebar.info(f"📅 系統日期：{datetime.now().strftime('%Y-%m-%d')}")

# --- 3. 股市數據抓取 ---
@st.cache_data(ttl=600)
def get_market_data():
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
st.subheader("🔥 今日漲幅排行前 10")
df_top10 = get_market_data()
st.dataframe(df_top10, use_container_width=True, hide_index=True)

st.divider()

# --- 4. AI 分析邏輯 ---
st.subheader("🤖 AI 近七天新聞深度分析")

if st.button("🚀 執行 AI 檢索 (需 API Key)"):
    if not user_api_key:
        st.error("❌ 請先在左側輸入您的 Gemini API Key。")
    else:
        try:
            genai.configure(api_key=user_api_key)
            
            # 【終極相容性修正】：嘗試不同的模型名稱路徑
            try:
                model = genai.GenerativeModel(model_name='models/gemini-1.5-flash')
                # 測試生成
                model.generate_content("test", generation_config={"max_output_tokens": 1})
            except:
                model = genai.GenerativeModel(model_name='models/gemini-pro')
            
            for _, row in df_top10.iterrows():
                ticker = row['代碼']
                with st.expander(f"🔍 查看 {ticker} 的分析報告"):
                    with st.spinner(f"正在分析 {ticker}..."):
                        prompt = f"請擔任專業分析師，總結股票 {ticker} 過去 7 天的重大財經新聞並給出繁體中文摘要。"
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
        
        except Exception as e:
            st.error(f"⚠️ 執行失敗。錯誤訊息：{str(e)}")
            st.info("提示：如果持續出現 404，請確認您的 API Key 是否在 Google AI Studio 中可以正常使用。")

st.caption("數據來源：yfinance & Google Gemini | 本工具不構成投資建議。")
