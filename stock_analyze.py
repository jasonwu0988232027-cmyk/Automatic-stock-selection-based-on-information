import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd

# --- 1. 配置 Gemini API ---
# 請在此處填入您的 Gemini API Key
# 建議使用 st.secrets 或環境變量來管理密鑰
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 設置 Streamlit 頁面 ---
st.set_page_config(page_title="AI 股市分析助手", layout="wide")
st.title("📈 股市熱門股 AI 新聞分析")

# 1. 調取現在日期與時間
now = datetime.now()
st.sidebar.info(f"當前系統時間：{now.strftime('%Y-%m-%d %H:%M:%S')}")

# --- 3. 獲取股市數據 (漲幅排行前 10) ---
@st.cache_data(ttl=3600)  # 快取 1 小時，避免頻繁請求
def get_top_gainers():
    # 這裡以美股 S&P 500 為例，或者您可以更換為特定板塊
    # 注意：yfinance 沒有直接的 "全市場漲幅排行" 接口，通常需要對一個清單進行過濾
    # 此處範例抓取一些熱門大型股作為演示，實際可接入專門的 API
    tickers = ["AAPL", "MSFT", "GOOGL", "AMZN", "NVDA", "TSLA", "META", "AMD", "NFLX", "INTC"]
    
    data_list = []
    for t in tickers:
        stock = yf.Ticker(t)
        hist = stock.history(period="2d")
        if len(hist) >= 2:
            prev_close = hist['Close'].iloc[-2]
            curr_close = hist['Close'].iloc[-1]
            change = (curr_close - prev_close) / prev_close * 100
            data_list.append({"代碼": t, "現價": round(curr_close, 2), "漲幅%": round(change, 2)})
    
    df = pd.DataFrame(data_list)
    return df.sort_values(by="漲幅%", ascending=False).head(10)

# --- 4. 使用 Gemini 查找並分析新聞 ---
def analyze_stock_news(stock_symbol):
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 3. 構造提示詞：查找近 7 天關於該股票的新聞
    prompt = f"""
    請擔任專業的財經分析師，針對股票代碼 '{stock_symbol}'，
    總結過去 7 天（截至 {now.date()}）內的重大相關新聞與市場動向。
    請包含以下內容：
    1. 三個關鍵新聞要點。
    2. 這些新聞對股價的潛在影響（看多/看空/中立）。
    請用繁體中文回答，條列式呈現。
    """
    
    try:
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini 分析出錯: {e}"

# --- 5. 介面呈現 ---
if st.button("點擊獲取今日漲幅前 10 並進行 AI 分析"):
    with st.spinner("正在獲取股市行情..."):
        top_10_df = get_top_gainers()
        st.subheader("🔥 今日熱門漲幅股票 (Top 10)")
        st.table(top_10_df)

    st.divider()
    
    st.subheader("🤖 Gemini AI 深度新聞分析 (近 7 天)")
    
    # 對前 10 名股票進行遍歷分析
    for index, row in top_10_df.iterrows():
        ticker = row['代碼']
        with st.expander(f"查看 {ticker} 的新聞分析 (今日漲幅: {row['漲幅%']}%)"):
            with st.spinner(f"正在分析 {ticker} 的近期資訊..."):
                analysis = analyze_stock_news(ticker)
                st.markdown(analysis)

else:
    st.write("請點擊上方按鈕開始分析。")

# --- 頁尾 ---
st.caption(f"數據來源：yfinance & Google Gemini AI | 分析日期：{now.date()}")
