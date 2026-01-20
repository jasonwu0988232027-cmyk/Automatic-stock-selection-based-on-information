import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 初始化設定 ---
st.set_page_config(page_title="AI 股市漲幅分析助手", layout="wide")

# 請在這裡輸入您的 Gemini API Key
# 建議從 https://aistudio.google.com/ 取得
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY"
genai.configure(api_key=GEMINI_API_KEY)

# --- 2. 定義功能函數 ---

def get_top_gainers():
    """獲取台股今日漲幅前 10 名 (以 Yahoo Finance 示例)"""
    # 這裡使用常見的熱門權值或特定清單模擬，因為 yf 暫無直接的 "台股漲幅排行" API
    # 實務上可串接爬蟲或第三方 API。此處演示獲取數據邏輯：
    tickers = ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW", "2412.TW", "2881.TW", "2882.TW", "2603.TW", "3008.TW"]
    
    data_list = []
    for t in tickers:
        stock = yf.Ticker(t)
        hist = stock.history(period="2d")
        if len(hist) >= 2:
            change = (hist['Close'].iloc[-1] - hist['Close'].iloc[-2]) / hist['Close'].iloc[-2] * 100
            data_list.append({
                "代碼": t,
                "名稱": stock.info.get('shortName', t),
                "現價": round(hist['Close'].iloc[-1], 2),
                "漲幅%": round(change, 2)
            })
    
    # 依照漲幅排序並取前10
    df = pd.DataFrame(data_list).sort_values(by="漲幅%", ascending=False).head(10)
    return df

def analyze_with_gemini(stock_list):
    """將股票清單交給 Gemini 進行聯網新聞查找與彙整"""
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    current_date = datetime.now().strftime("%Y-%m-%d")
    seven_days_ago = (datetime.now() - timedelta(days=7)).strftime("%Y-%m-%d")
    
    # 建立 Prompt
    stock_str = ", ".join([f"{row['名稱']}({row['代碼']})" for _, row in stock_list.iterrows()])
    
    prompt = f"""
    今天是 {current_date}。
    請針對以下 10 檔目前漲幅領先的股票：{stock_str}。
    
    任務：
    1. 查找這 10 檔股票在近 7 天內（{seven_days_ago} 至今）的相關重大新聞或公告。
    2. 根據新聞內容，分析各個股票所屬「行業」目前的整體表現與成績。
    3. 請嚴格以 Markdown 表格格式回傳，表格欄位必須包含：
       | 股票名稱 | 所屬行業 | 近七天重大新聞摘要 | 行業成績/趨勢分析 |
    
    請用繁體中文回答。
    """
    
    with st.spinner("Gemini 正在搜尋近 7 天新聞並分析中..."):
        response = model.generate_content(prompt)
        return response.text

# --- 3. Streamlit 介面渲染 ---

st.title("🚀 今日股市漲幅 Top 10 與 AI 深度分析")
st.write(f"目前時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("開始獲取數據並分析"):
    # 步驟 1 & 2: 獲取日期與漲幅排行
    top_stocks = get_top_gainers()
    
    st.subheader("📈 當前漲幅排行前 10 名")
    st.table(top_stocks)
    
    # 步驟 3 & 4: 詢問 Gemini 並展示表格
    analysis_result = analyze_with_gemini(top_stocks)
    
    st.subheader("🤖 Gemini AI 行業成績彙整分析")
    st.markdown(analysis_result)

else:
    st.info("請點擊上方按鈕開始自動化流程。")
