import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime
import pandas as pd

# --- 1. 頁面配置 ---
st.set_page_config(page_title="AI 股市分析助手", layout="wide", page_icon="📈")
st.title("📈 股市熱門股 AI 新聞分析系統")

# --- 2. 側邊欄：權限獲取與設置 ---
st.sidebar.header("🔑 權限設置")
user_api_key = st.sidebar.text_input(
    "輸入您的 Gemini API Key", 
    type="password", 
    help="請從 Google AI Studio 獲取金鑰"
)

def validate_and_configure_api(api_key):
    """驗證金鑰並配置 Gemini"""
    if not api_key:
        st.sidebar.warning("⚠️ 請先輸入 API 金鑰。")
        return False
    try:
        genai.configure(api_key=api_key)
        # 使用 -latest 確保模型路徑正確，並進行極小量測試
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        model.generate_content("Hi") 
        st.sidebar.success("✅ 金鑰驗證成功！")
        return True
    except Exception as e:
        # 攔截 404 或 401 等常見錯誤
        st.sidebar.error(f"❌ 權限錯誤：{e}")
        return False

# 執行驗證
is_ready = validate_and_configure_api(user_api_key)

# 顯示目前日期
now = datetime.now()
st.sidebar.info(f"📅 系統日期：{now.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 3. 核心功能函數 ---

@st.cache_data(ttl=3600)  # 快取一小時，避免頻繁請求 API
def get_top_gainers():
    """獲取預設股票清單中漲幅前 10 的股票"""
    # 範例清單：大型美股與熱門科技股
    tickers = ["AAPL", "NVDA", "TSLA", "MSFT", "GOOGL", "AMD", "META", "AMZN", "NFLX", "AVGO", "SMCI", "ARM"]
    data_list = []
    
    for t in tickers:
        try:
            stock = yf.Ticker(t)
            hist = stock.history(period="2d")
            if len(hist) >= 2:
                prev_close = hist['Close'].iloc[-2]
                curr_close = hist['Close'].iloc[-1]
                change = (curr_close - prev_close) / prev_close * 100
                data_list.append({
                    "代碼": t, 
                    "現價 (USD)": round(curr_close, 2), 
                    "今日漲幅%": round(change, 2)
                })
        except Exception:
            continue
            
    df = pd.DataFrame(data_list)
    return df.sort_values(by="今日漲幅%", ascending=False).head(10)

def analyze_with_gemini(stock_symbol):
    """調用 Gemini 查找並分析新聞"""
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        prompt = f"""
        請擔任專業財經分析師，針對股票 '{stock_symbol}'，總結過去 7 天（截至 {now.date()}）內的重大相關新聞。
        請包含：
        1. 三個關鍵新聞要點。
        2. 這些新聞對股價的潛在影響（看多/看空/中立）。
        請用繁體中文回答，條列式呈現，語氣專業。
        """
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"分析時發生錯誤: {str(e)}"

# --- 4. 主介面邏輯 ---

if is_ready:
    if st.button("🚀 開始獲取漲幅排行並分析"):
        with st.spinner("正在獲取實時行情數據..."):
            df = get_top_gainers()
            st.subheader("🔥 今日漲幅排行前 10 (熱門股)")
            st.dataframe(df, use_container_width=True, hide_index=True)

        st.divider()
        st.subheader("📋 Gemini AI 深度新聞分析 (近 7 天)")
        
        # 遍歷前 10 名進行分析
        for _, row in df.iterrows():
            ticker = row['代碼']
            with st.expander(f"🔍 查看 {ticker} 的近期動向 (漲幅: {row['今日漲幅%']}%)"):
                with st.spinner(f"Gemini 正在檢索 {ticker} 的資訊..."):
                    res = analyze_with_gemini(ticker)
                    st.markdown(res)
else:
    # 未輸入金鑰時的顯示畫面
    st.info("💡 請在左側側邊欄輸入有效的 Gemini API Key 即可啟動 AI 分析功能。")
    
    col1, col2 = st.columns(2)
    with col1:
        st.markdown("""
        ### 如何獲取 Gemini API Key？
        1. 前往 [Google AI Studio](https://aistudio.google.com/)。
        2. 登錄您的 Google 帳號。
        3. 點擊左側 **"Get API key"**。
        4. 點擊 **"Create API key in new project"**。
        5. 複製金鑰並貼上到本程式左側。
        """)
    with col2:
        st.image("https://blog.google/static/blog/images/google-logo.svg", width=100) # 裝飾用
        st.caption("本工具使用 Google Gemini 1.5 Flash 模型進行數據總結。")

# --- 頁尾 ---
st.divider()
st.caption(f"免責聲明：本工具僅供參考，不構成任何投資建議。數據來源：yfinance & Google AI。")
