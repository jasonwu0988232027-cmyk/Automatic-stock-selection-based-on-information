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

# --- 3. 股市數據抓取函數 (yfinance 不需要 Key) ---
@st.cache_data(ttl=600)
def get_market_data():
    # 預設熱門美股清單
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

# --- 4. 主介面：顯示股市數據 ---
st.subheader("🔥 今日漲幅排行前 10")
df_top10 = get_market_data()
st.dataframe(df_top10, use_container_width=True, hide_index=True)

st.divider()

# --- 5. AI 分析邏輯 ---
st.subheader("🤖 AI 近七天新聞深度分析")

if st.button("🚀 執行 AI 檢索 (需 API Key)"):
    if not user_api_key:
        st.error("❌ 請先在左側輸入您的 Gemini API Key。")
    else:
        try:
            # 配置 Gemini
            genai.configure(api_key=user_api_key)
            
            # 【關鍵修正】：使用最基礎的模型名稱，避免 404 錯誤
            # 行號參考：約在第 56 行
            model = genai.GenerativeModel('gemini-1.5-flash') 
            
            for _, row in df_top10.iterrows():
                ticker = row['代碼']
                with st.expander(f"🔍 查看 {ticker} 的分析報告"):
                    with st.spinner(f"正在分析 {ticker}..."):
                        prompt = f"請擔任專業分析師，總結股票 {ticker} 過去 7 天的重大財經新聞並給出繁體中文摘要。"
                        response = model.generate_content(prompt)
                        st.markdown(response.text)
        
        except Exception as e:
            # 擷取具體錯誤訊息
            error_msg = str(e)
            if "404" in error_msg:
                st.error("⚠️ 404 錯誤：模型名稱不匹配。請確認您的 SDK 版本已更新。")
            elif "403" in error_msg:
                st.error("⚠️ 403 錯誤：您的 IP 地區不支援（請嘗試切換 VPN 至美國/台灣）。")
            else:
                st.error(f"⚠️ 發生錯誤：{error_msg}")

st.caption("數據來源：yfinance & Google Gemini | 本工具不構成投資建議。")
