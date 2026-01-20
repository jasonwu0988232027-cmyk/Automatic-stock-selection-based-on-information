import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta
import time

# --- 1. 頁面配置 ---
st.set_page_config(page_title="股市 AI 分析儀", layout="wide")

# --- 2. 側邊欄：安全輸入 ---
with st.sidebar:
    st.header("設置")
    api_key = st.text_input("請輸入 Gemini API Key", type="password")
    # 允許用戶切換模型，增加靈活性
    model_choice = st.selectbox("選擇 AI 模型", ["gemini-1.5-flash", "gemini-1.5-pro", "gemini-pro"])

# --- 3. 核心功能：穩定的股市數據抓取 ---
@st.cache_data(ttl=3600)  # 緩存 1 小時，這是解決 RateLimit 的關鍵
def fetch_stock_data():
    # 預設台股前 10 大權值股，避免全市場掃描觸發封鎖
    target_stocks = ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW", 
                     "2412.TW", "2881.TW", "2882.TW", "2603.TW", "3008.TW"]
    
    try:
        # 使用下載模式而非 Ticker 模式，減少 Connection 數量
        data = yf.download(target_stocks, period="2d", interval="1d", progress=False)
        
        stock_list = []
        for ticker in target_stocks:
            if ticker in data['Close']:
                prices = data['Close'][ticker].dropna()
                if len(prices) >= 2:
                    current_price = prices.iloc[-1]
                    prev_price = prices.iloc[-2]
                    change_pct = ((current_price - prev_price) / prev_price) * 100
                    stock_list.append({
                        "代碼": ticker,
                        "價格": round(current_price, 2),
                        "漲跌幅(%)": round(change_pct, 2)
                    })
        
        return pd.DataFrame(stock_list).sort_values(by="漲跌幅(%)", ascending=False)
    except Exception as e:
        st.error(f"股市數據讀取失敗: {e}")
        return pd.DataFrame()

# --- 4. 核心功能：AI 分析 (修正 404 錯誤) ---
def get_ai_analysis(df, key, model_name):
    if not key:
        return "請先輸入 API Key。"
    
    genai.configure(api_key=key)
    
    # 修正模型名稱調用邏輯
    try:
        # 針對 404 錯誤，改用最基礎的模型字串，不加 -latest
        model = genai.GenerativeModel(model_name)
        
        prompt = f"""
        現在日期：{datetime.now().strftime('%Y-%m-%d')}
        分析目標股票清單：{df['代碼'].tolist()}
        
        任務：
        1. 檢索過去 7 天內關於這些股票的重大新聞。
        2. 分析各股票所屬行業的成績與趨勢。
        3. 輸出一個 Markdown 表格，包含：股票名稱、行業、近七天新聞摘要、行業表現評分。
        
        語言：繁體中文。
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"AI 分析發生錯誤: {str(e)}\n建議：請確認 API Key 是否擁有該模型的存取權限。"

# --- 5. Streamlit 主介面 ---
st.title("📈 股市即時漲幅與行業分析報告")
st.info(f"📅 目前時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("執行分析任務"):
    # 第一步：顯示漲幅
    with st.status("獲取行情數據中...") as status:
        top_stocks_df = fetch_stock_data()
        if not top_stocks_df.empty:
            status.update(label="行情數據獲取成功！", state="complete")
            st.subheader("🔥 今日漲幅排行 (Top 10)")
            st.dataframe(top_stocks_df, use_container_width=True)
            
            # 第二步：AI 分析
            st.divider()
            st.subheader("🤖 Gemini AI 行業成績整理")
            with st.spinner("AI 正在查找新聞並分析行業成績..."):
                analysis_report = get_ai_analysis(top_stocks_df, api_key, model_choice)
                st.markdown(analysis_report)
        else:
            status.update(label="數據獲取失敗，可能被 Yahoo 暫時限流。", state="error")
            st.warning("提示：請嘗試更換網路環境（如手機熱點）或稍後再試。")
