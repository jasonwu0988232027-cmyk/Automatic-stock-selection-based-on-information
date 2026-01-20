import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime
import pandas as pd

# --- 1. 頁面配置 ---
st.set_page_config(page_title="AI 股市金鑰驗證助手", layout="wide")
st.title("📈 股市熱門股 AI 分析系統")

# --- 2. 側邊欄：權限獲取與設置 ---
st.sidebar.header("🔑 權限設置")
user_api_key = st.sidebar.text_input("輸入您的 Gemini API Key", type="password", help="請從 Google AI Studio 獲取金鑰")

def validate_and_configure_api(api_key):
    """驗證金鑰是否可用"""
    if not api_key:
        st.sidebar.warning("⚠️ 請先輸入 API 金鑰以啟用分析功能。")
        return False
    try:
        genai.configure(api_key=api_key)
        # 進行一個極小規模的測試調用以確認權限
        model = genai.GenerativeModel('gemini-1.5-flash')
        model.generate_content("test")
        st.sidebar.success("✅ 金鑰驗證成功！")
        return True
    except Exception as e:
        st.sidebar.error(f"❌ 金鑰無效或權限錯誤: {e}")
        return False

is_ready = validate_and_configure_api(user_api_key)

# 顯示目前日期
now = datetime.now()
st.sidebar.info(f"📅 查詢日期：{now.strftime('%Y-%m-%d')}")

# --- 3. 核心功能函數 ---
@st.cache_data(ttl=3600)
def get_top_gainers():
    # 模擬熱門股名單 (以美股為例)
    tickers = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMD", "META", "AMZN", "NFLX", "AVGO"]
    data_list = []
    for t in tickers:
        stock = yf.Ticker(t)
        hist = stock.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            curr_close = hist['Close'].iloc[-1]
            change = (curr_close - prev_close) / prev_close * 100
            data_list.append({"代碼": t, "現價": round(curr_close, 2), "漲幅%": round(change, 2)})
    return pd.DataFrame(data_list).sort_values(by="漲幅%", ascending=False).head(10)

def analyze_with_gemini(stock_symbol, api_key):
    """調用 Gemini 查找近 7 天新聞"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    prompt = f"請分析股票 {stock_symbol} 在過去 7 天內的重大財經新聞，並提供中文摘要與看盤建議。"
    response = model.generate_content(prompt)
    return response.text

# --- 4. 主介面邏輯 ---
if is_ready:
    if st.button("🚀 開始分析今日漲幅前 10 股票"):
        with st.spinner("正在獲取實時行情..."):
            df = get_top_gainers()
            st.subheader("🔥 今日漲幅排行前 10")
            st.dataframe(df, use_container_width=True)

        st.divider()
        st.subheader("📋 AI 新聞深度分析")
        
        for _, row in df.iterrows():
            ticker = row['代碼']
            with st.expander(f"🔍 點擊展開 {ticker} 的近七天動向"):
                with st.spinner(f"Gemini 正在檢索 {ticker} 的新聞..."):
                    res = analyze_with_gemini(ticker, user_api_key)
                    st.markdown(res)
else:
    st.info("💡 請在左側輸入有效的 Gemini API Key 即可解鎖分析功能。")
    st.markdown("""
    ### 如何獲取權限？
    1. 前往 [Google AI Studio](https://aistudio.google.com/)。
    2. 登錄您的 Google 帳號。
    3. 點擊 **"Get API key"** 並創建新金鑰。
    4. 將金鑰複製並貼上到左側輸入框。
    """)
