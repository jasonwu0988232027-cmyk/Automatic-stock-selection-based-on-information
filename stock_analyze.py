import streamlit as st
import yfinance as yf
import google.generativeai as genai
from datetime import datetime, timedelta
import pandas as pd

st.set_page_config(page_title="股市 AI 診斷", layout="wide")

# --- 側邊欄權限驗證 ---
st.sidebar.header("🔑 API 權限驗證")
user_api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password")

def test_gemini_connection(api_key):
    if not api_key:
        return False, "請輸入金鑰"
    try:
        genai.configure(api_key=api_key)
        # 測試連線與模型可用性
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        # 嘗試一個超簡短生成的測試
        response = model.generate_content("ping", generation_config={"max_output_tokens": 5})
        return True, "驗證成功"
    except Exception as e:
        # 回傳具體的錯誤原因
        error_msg = str(e)
        if "API_KEY_INVALID" in error_msg:
            return False, "金鑰無效 (請檢查是否複製完整)"
        elif "403" in error_msg:
            return False, "權限遭拒 (可能是地區限制或帳號未啟用)"
        else:
            return False, f"連線失敗: {error_msg}"

is_valid, status_msg = test_gemini_connection(user_api_key)

if user_api_key:
    if is_valid:
        st.sidebar.success(status_msg)
    else:
        st.sidebar.error(status_msg)

# --- 核心邏輯 ---
@st.cache_data(ttl=600)
def get_market_data():
    # 使用標普500中較具代表性的股票
    tickers = ["NVDA", "TSLA", "AAPL", "AMD", "MSFT", "GOOGL", "AMZN", "META", "NFLX", "AVGO"]
    results = []
    for t in tickers:
        try:
            s = yf.Ticker(t)
            h = s.history(period="2d")
            if len(h) >= 2:
                change = (h['Close'].iloc[-1] - h['Close'].iloc[-2]) / h['Close'].iloc[-2] * 100
                results.append({"代碼": t, "現價": round(h['Close'].iloc[-1], 2), "漲幅%": round(change, 2)})
        except: continue
    return pd.DataFrame(results).sort_values("漲幅%", ascending=False).head(10)

# --- UI 介面 ---
st.title("📊 股市熱門股 AI 診斷")
st.info(f"當前時間：{datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")

if is_valid:
    if st.button("獲取今日排行並分析"):
        df = get_market_data()
        st.table(df)
        
        st.subheader("🤖 AI 近七天新聞分析")
        model = genai.GenerativeModel('gemini-1.5-flash-latest')
        
        for _, row in df.iterrows():
            with st.expander(f"查看 {row['代碼']} 分析"):
                try:
                    prompt = f"分析股票 {row['代碼']} 過去 7 天的新聞摘要與對股價的看多/看空建議。請用繁體中文回答。"
                    res = model.generate_content(prompt)
                    st.write(res.text)
                except Exception as e:
                    st.error(f"分析失敗: {e}")
else:
    st.warning("請在左側輸入正確的金鑰以啟用功能。")
