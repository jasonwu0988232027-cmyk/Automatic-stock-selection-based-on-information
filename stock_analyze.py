import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
from datetime import datetime, timedelta

# --- 1. 初始化設定 ---
st.set_page_config(page_title="股市 AI 分析助手", layout="wide")

# 側邊欄配置 API Key
GEMINI_API_KEY = st.sidebar.text_input("輸入 Gemini API Key", type="password")

# --- 2. 核心功能函數 ---

@st.cache_data(ttl=3600)  # 緩存一小時，防止頻繁請求被 Yahoo 封鎖
def get_stock_ranking():
    """獲取台股預設清單的漲幅數據"""
    # 預設熱門股，減少請求壓力
    tickers = ["2330.TW", "2317.TW", "2454.TW", "2303.TW", "2382.TW", 
               "2412.TW", "2881.TW", "2882.TW", "2603.TW", "3008.TW"]
    
    results = []
    # 使用一次性下載模式更穩定
    data = yf.download(tickers, period="2d", group_by='ticker', progress=False)
    
    for t in tickers:
        try:
            # 取得該股的 Close 序列
            s_data = data[t]['Close']
            if len(s_data) >= 2:
                now = s_data.iloc[-1]
                prev = s_data.iloc[-2]
                change = ((now - prev) / prev) * 100
                results.append({"股票代碼": t, "現價": round(now, 2), "漲幅%": round(change, 2)})
        except:
            continue
            
    df = pd.DataFrame(results).sort_values(by="漲幅%", ascending=False).head(10)
    return df

def ask_gemini_analysis(stock_df):
    """詢問 Gemini 關於新聞與行業的分析"""
    if not GEMINI_API_KEY:
        return "請提供 API Key 以進行分析。"
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # 修正 404 錯誤：使用最通用的 'gemini-pro' 或 'models/gemini-1.5-flash-latest'
    try:
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        stock_list_str = ", ".join(stock_df["股票代碼"].tolist())
        prompt = f"""
        今天是 {datetime.now().strftime('%Y-%m-%d')}。
        請針對這10檔漲幅領先股票進行分析：{stock_list_str}。
        1. 搜尋近 7 天內關於這些股票或其所屬產業的重大新聞。
        2. 整理成一個 Markdown 表格。
        3. 表格欄位：| 股票名稱 | 所屬行業 | 近七天新聞摘要 | 行業成績/前景分析 |
        請使用繁體中文。
        """
        
        response = model.generate_content(prompt)
        return response.text
    except Exception as e:
        return f"Gemini 分析出錯：{str(e)}。建議確認 API Key 是否有效，或嘗試更換模型名稱。"

# --- 3. Streamlit UI 介面 ---

st.title("🚀 股市漲幅 Top 10 與 AI 深度分析")
st.write(f"當前查詢時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if st.button("開始執行自動化分析"):
    if not GEMINI_API_KEY:
        st.error("請在側邊欄填寫您的 Gemini API Key！")
    else:
        # 第一步：獲取數據
        with st.spinner("正在獲取股市數據..."):
            top_df = get_stock_ranking()
            
        if not top_df.empty:
            st.subheader("📈 今日漲幅前 10 名 (範例清單)")
            st.dataframe(top_df, use_container_width=True)
            
            # 第二步：AI 分析
            with st.spinner("Gemini 正在搜尋新聞並整理表格..."):
                report = ask_gemini_analysis(top_df)
                st.divider()
                st.subheader("🤖 AI 行業分析報告 (近七天新聞整理)")
                st.markdown(report)
        else:
            st.error("無法從 Yahoo Finance 獲取數據。這通常是 IP 被暫時限制，請稍後再試或更換網路環境。")
