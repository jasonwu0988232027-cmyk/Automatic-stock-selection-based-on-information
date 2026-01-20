import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta
import time

# --- 1. 初始化與頁面設定 ---
st.set_page_config(page_title="AI 股市分析助手", layout="wide")

# 配置 Gemini API
# 建議將 API KEY 存在 Streamlit Secrets 中以確保安全
GEMINI_API_KEY = st.sidebar.text_input("輸入 Gemini API Key", type="password")
if GEMINI_API_KEY:
    genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 核心功能函數 ---

@st.cache_data(ttl=3600)  # 緩存 1 小時，避免頻繁請求觸發 Rate Limit
def get_safe_stock_data():
    """使用較安全的方式獲取數據，避免觸發 Yahoo 限制"""
    # 預設觀察清單 (台股熱門股)
    tickers = ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW", 
               "2412.TW", "2881.TW", "2882.TW", "2603.TW", "3008.TW"]
    
    # 一次性下載所有數據，比一個個下載更不容易被封鎖
    data = yf.download(tickers, period="2d", interval="1d", progress=False)
    
    result_list = []
    for ticker in tickers:
        try:
            # 獲取最後兩個交易日的收盤價
            close_prices = data['Close'][ticker]
            if len(close_prices) >= 2:
                current_price = close_prices.iloc[-1]
                prev_price = close_prices.iloc[-2]
                change_pct = ((current_price - prev_price) / prev_price) * 100
                
                result_list.append({
                    "股票代碼": ticker,
                    "當前價格": round(current_price, 2),
                    "漲跌幅(%)": round(change_pct, 2)
                })
        except Exception:
            continue
            
    # 排序取前 10
    df = pd.DataFrame(result_list).sort_values(by="漲跌幅(%)", ascending=False).head(10)
    return df

def get_gemini_analysis(df_stocks):
    """驅動 Gemini 進行新聞搜尋與行業統整"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    # 準備提示詞
    stock_names = ", ".join(df_stocks["股票代碼"].tolist())
    prompt = f"""
    現在日期是 {datetime.now().strftime('%Y-%m-%d')}。
    請針對以下這 10 檔股票進行分析：{stock_names}。
    
    任務要求：
    1. 檢索這 10 檔股票在過去 7 天內的重大財經新聞。
    2. 總結每檔股票所屬行業的近期表現。
    3. 將結果整理成一個 Markdown 表格，包含：股票代碼、所屬行業、近七天新聞摘要、行業成績評分(1-10)。
    
    請使用繁體中文回答。
    """
    
    response = model.generate_content(prompt)
    return response.text

# --- 3. Streamlit UI 介面 ---

st.title("📊 股市漲幅 Top 10 與 AI 行業分析")
st.caption(f"數據調取時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if not GEMINI_API_KEY:
    st.warning("請先在側邊欄輸入 Gemini API Key 才能執行 AI 分析。")

if st.button("執行自動化分析任務"):
    try:
        # 步驟 1 & 2: 獲取數據
        with st.status("正在從 Yahoo Finance 獲取即時數據...", expanded=True) as status:
            df_top10 = get_safe_stock_data()
            st.write("已成功獲取今日漲幅數據。")
            st.table(df_top10)
            
            # 步驟 3 & 4: AI 分析
            st.write("正在啟動 Gemini 聯網分析與新聞統整...")
            if GEMINI_API_KEY:
                analysis_report = get_gemini_analysis(df_top10)
                status.update(label="分析完成！", state="complete", expanded=False)
                
                st.divider()
                st.subheader("🤖 Gemini AI 行業分析報告")
                st.markdown(analysis_report)
            else:
                status.update(label="數據獲取成功，但缺少 API Key 以進行分析。", state="error")
                
    except Exception as e:
        st.error(f"發生錯誤：{str(e)}")
        st.info("提示：這通常是 Yahoo Finance 的暫時性限制，請稍候再試或更換網路環境。")
