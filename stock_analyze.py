import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import time

# --- 1. 配置 Gemini API ---
# 請在此處輸入您的 API Key 或從 Streamlit Secrets 讀取
GEMINI_API_KEY = "YOUR_GEMINI_API_KEY" 
genai.configure(api_key=GEMINI_API_KEY)
model = genai.GenerativeModel('gemini-1.5-flash')

# --- 2. 網頁配置 ---
st.set_page_config(page_title="AI 產業權值百科 v15", layout="wide")

# --- 3. 股票清單 (縮減展示用，可自行擴充您原本的清單) ---
STOCK_DICT = {
    "1802.TW": "台玻", "2330.TW": "台積電", "2408.TW": "南亞科", 
    "2409.TW": "友達", "2317.TW": "鴻海", "2603.TW": "長榮",
    "NVDA": "輝達", "AAPL": "蘋果", "TSLA": "特斯拉"
}

# --- 4. 核心功能：Gemini 新聞評分 ---
def get_ai_sentiment_score(ticker, stock_name):
    """
    抓取新聞並利用 Gemini 進行情緒與資訊面量化評分
    """
    try:
        s = yf.Ticker(ticker)
        news_list = s.news[:3] # 取最近三則
        if not news_list:
            return 50, "無近期新聞"

        context = "\n".join([f"- {n['title']}" for n in news_list])
        prompt = f"""
        你是一位專業台股分析師。請針對「{stock_name}({ticker})」的以下新聞進行量化評分：
        {context}
        
        任務：
        1. 判斷對股價的利多程度（0-100分，50為中立）。
        2. 給出一個15字以內的理由。
        3. 以 JSON 格式輸出：{{"score": 分數, "reason": "原因"}}
        """
        
        response = model.generate_content(prompt)
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        result = json.loads(res_text)
        return result['score'], result['reason']
    except:
        return 50, "AI 服務暫時無法取得"

# --- 5. 核心功能：綜合掃描 ---
def analyze_stock(ticker, weights):
    try:
        # 下載數據
        df = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # A. 技術面計算
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        tech_score = 0
        reasons = []
        
        if float(curr['RSI']) < 30: 
            tech_score += weights['rsi']; reasons.append("RSI超賣")
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            tech_score += weights['ma']; reasons.append("MA金叉")
        
        chg = ((float(curr['Close']) - float(prev['Close'])) / float(prev['Close'])) * 100
        if abs(chg) >= 7.0:
            tech_score += weights['vol']; reasons.append(f"劇烈波動({round(chg,1)}%)")
        if float(curr['Volume']) > df['Volume'].mean() * 2:
            tech_score += weights['vxx']; reasons.append("爆量")

        # B. 資訊面計算 (Gemini AI)
        ai_raw_score, ai_reason = get_ai_sentiment_score(ticker, STOCK_DICT.get(ticker, ticker))
        # 將 0-100 映射到權重 (50分以上才加分)
        info_score = (max(0, ai_raw_score - 50) / 50) * weights['news']
        if info_score > (weights['news'] * 0.2):
            reasons.append(f"AI利多:{ai_reason}")

        total_score = tech_score + info_score

        return {
            "名稱": STOCK_DICT.get(ticker, ticker),
            "代碼": ticker,
            "綜合總分": round(total_score, 1),
            "現價": round(float(curr['Close']), 2),
            "漲跌幅": f"{round(chg, 2)}%",
            "判定訊號": " | ".join(reasons),
            "AI評分": ai_raw_score,
            "raw_score": total_score
        }
    except Exception as e:
        return None

# --- 6. UI 介面 ---
st.sidebar.title("🛠️ 策略權重設定")
with st.sidebar.expander("⚖️ 權重分配 (總分制)", expanded=True):
    w_rsi = st.slider("RSI 超賣權重", 0, 100, 30)
    w_ma = st.slider("MA 金叉權重", 0, 100, 20)
    w_vol = st.slider("劇烈波動權重", 0, 100, 15)
    w_vxx = st.slider("成交爆量權重", 0, 100, 10)
    w_news = st.slider("Gemini 資訊面權重", 0, 100, 25)

threshold = st.sidebar.slider("推薦門檻分數", 0, 150, 40)

st.title("🏆 AI 財經資訊與量化掃描系統")

if st.button("🚀 開始全自動掃描 (技術面 + Gemini 資訊面)"):
    results = []
    progress_bar = st.progress(0)
    tickers = list(STOCK_DICT.keys())
    
    for idx, t in enumerate(tickers):
        res = analyze_stock(t, {
            'rsi': w_rsi, 'ma': w_ma, 'vol': w_vol, 'vxx': w_vxx, 'news': w_news
        })
        if res: results.append(res)
        progress_bar.progress((idx + 1) / len(tickers))
        time.sleep(1) # 避免 Gemini API 頻率限制

    if results:
        df_res = pd.DataFrame(results).sort_values("raw_score", ascending=False)
        st.dataframe(df_res[df_res['raw_score'] >= threshold].drop(columns=['raw_score']), use_container_width=True)
    else:
        st.error("掃描失敗或無符合標的。")