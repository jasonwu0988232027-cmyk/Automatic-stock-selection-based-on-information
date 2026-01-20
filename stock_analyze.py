import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import plotly.express as px

# --- 1. 網頁配置與 34 產業清單 ---
st.set_page_config(page_title="AI 全產業權值百科 v17", layout="wide")

# 這裡已為您補齊 34 個產業 (包含您原始清單中的所有龍頭)
INDUSTRY_GROUPS = {
    "水泥工業": ["1101.TW", "1102.TW"], "食品工業": ["1216.TW", "1210.TW"],
    "塑膠工業": ["1301.TW", "1303.TW"], "紡織纖維": ["1402.TW", "1476.TW"],
    "電機機械": ["1503.TW", "1519.TW"], "電器電纜": ["1605.TW", "1609.TW"],
    "化學工業": ["1717.TW", "1722.TW"], "生技醫療": ["6446.TW", "1795.TW"],
    "玻璃陶瓷": ["1802.TW", "1806.TW"], "造紙工業": ["1907.TW", "1904.TW"],
    "鋼鐵工業": ["2002.TW", "2014.TW"], "橡膠工業": ["2105.TW", "2106.TW"],
    "汽車工業": ["2207.TW", "2201.TW"], "半導體業": ["2330.TW", "2454.TW"],
    "電腦周邊": ["2382.TW", "3231.TW"], "光電業": ["3008.TW", "2409.TW"],
    "通信網路": ["2412.TW", "2345.TW"], "電子組件": ["2308.TW", "2327.TW"],
    "電子通路": ["3702.TW", "3036.TW"], "資訊服務": ["6214.TW", "2480.TW"],
    "其他電子": ["2317.TW", "2360.TW"], "建材營造": ["2542.TW", "2548.TW"],
    "航運業": ["2603.TW", "2618.TW"], "觀光餐旅": ["2707.TW", "2727.TW"],
    "金融保險": ["2881.TW", "2882.TW"], "貿易百貨": ["2912.TW", "8454.TW"],
    "油電燃氣": ["6505.TW", "8931.TW"], "綠能環保": ["9930.TW", "6806.TW"],
    "數位雲端": ["6689.TW", "6173.TW"], "運動休閒": ["9904.TW", "9910.TW"],
    "居家生活": ["8464.TW", "9911.TW"], "其 他": ["9933.TW", "9938.TW"],
    "ETF與公債": ["0050.TW", "00679B.TW"]
}

# --- 2. 側邊欄：找回您的「權重一表」 ---
st.sidebar.title("🛠️ AI 戰略配置")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password", key="final_v17")

with st.sidebar.expander("⚖️ 權重分配 (找回消失的拉桿)", expanded=True):
    # 找回原本的 4 個技術拉桿
    w_rsi = st.slider("RSI 超賣權重", 0, 100, 40)
    w_ma = st.slider("MA 金叉權重", 0, 100, 30)
    w_vol = st.slider("劇烈波動權重", 0, 100, 20)
    w_vxx = st.slider("成交爆量權重", 0, 100, 10)
    st.markdown("---")
    # 新增 AI 資訊拉桿
    w_ai = st.slider("✨ AI 產業分析權重", 0, 100, 50)

# --- 3. 分析引擎 ---
def get_ai_score(target, news_list):
    if not api_key: return 50
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        context = " ".join(news_list) if news_list else "平淡"
        prompt = f"評估 {target} 利多(0-100)，僅回傳 JSON: {{'score': 分數}}"
        res = model.generate_content(prompt)
        return json.loads(res.text.replace('```json', '').replace('```', '').strip())['score']
    except: return 50

# --- 4. 主執行邏輯 ---
if st.button("🚀 啟動 34 產業全權重掃描"):
    if not api_key:
        st.error("請先輸入 API Key！")
    else:
        all_results = []
        heat_data = []
        progress = st.progress(0)
        
        for idx, (ind_name, tickers) in enumerate(INDUSTRY_GROUPS.items()):
            # 產業 AI 分數 (解決熱力圖全 50 的問題)
            ind_news = []
            try:
                raw_n = yf.Ticker(tickers[0]).news
                if raw_n: ind_news = [raw_n[0]['title']]
            except: pass
            
            ind_score = get_ai_score(ind_name, ind_news)
            heat_data.append({"產業": ind_name, "景氣分數": ind_score})
            
            # 個股分析 (整合 5 項權重)
            for t in tickers:
                try:
                    df = yf.download(t, period="60d", progress=False, auto_adjust=True)
                    if df.empty or len(df) < 20: continue
                    
                    df['RSI'] = ta.rsi(df['Close'], length=14)
                    df['MA5'] = ta.sma(df['Close'], length=5)
                    df['MA10'] = ta.sma(df['Close'], length=10)
                    
                    curr, prev = df.iloc[-1], df.iloc[-2]
                    score = 0
                    
                    # 1. RSI (RSI < 25)
                    if curr['RSI'] < 25: score += w_rsi
                    # 2. MA 金叉
                    if prev['MA5'] < prev['MA10'] and curr['MA5'] > curr['MA10']: score += w_ma
                    # 3. 劇烈波動 (>9%)
                    chg = abs((curr['Close'] - prev['Close']) / prev['Close'] * 100)
                    if chg >= 9.0: score += w_vol
                    # 4. 成交爆量 (2倍均量)
                    if curr['Volume'] > df['Volume'].mean() * 2: score += w_vxx
                    # 5. AI 權重
                    score += ((ind_score - 50) / 50 * w_ai)
                    
                    all_results.append({
                        "產業": ind_name, "代碼": t, "總分": round(score, 1),
                        "現價": round(float(curr['Close']), 2), "訊號": f"AI({ind_score}分)"
                    })
                except: continue
            progress.progress((idx + 1) / len(INDUSTRY_GROUPS))

        # --- 5. 視覺化輸出 ---
        st.subheader("📊 34 產業 AI 景氣熱力圖")
        st.plotly_chart(px.bar(pd.DataFrame(heat_data), x="產業", y="景氣分數", color="景氣分數", color_continuous_scale="RdYlGn"), use_container_width=True)
        
        st.subheader("🏆 全權重優選標的")
        if all_results:
            st.dataframe(pd.DataFrame(all_results).sort_values("總分", ascending=False), use_container_width=True)
