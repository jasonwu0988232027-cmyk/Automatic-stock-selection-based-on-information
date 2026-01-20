import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import plotly.express as px

# --- 1. 網頁配置與 34 產業清單 ---
st.set_page_config(page_title="AI 全產業權值百科 v17", layout="wide")

import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import time
import plotly.express as px

# --- 1. 網頁配置與資料庫 ---
st.set_page_config(page_title="AI 產業戰略百科 v16", layout="wide")

# --- 1. 股票字典與連動映射表 ---
# 包含您提供的 34 個產業前 10 龍頭
INDUSTRY_GROUPS = {
    "水泥工業": ["1101.TW", "1102.TW", "1108.TW", "1109.TW", "1110.TW"],
    "食品工業": ["1216.TW", "1210.TW", "1215.TW", "1227.TW", "1229.TW", "1231.TW"],
    "塑膠工業": ["1301.TW", "1303.TW", "1326.TW", "1304.TW", "1308.TW", "1309.TW"],
    "紡織纖維": ["1402.TW", "1476.TW", "1477.TW", "1409.TW", "1444.TW"],
    "電器機械": ["1503.TW", "1504.TW", "1513.TW", "1519.TW", "1560.TW", "1590.TW"],
    "電器電纜": ["1605.TW", "1608.TW", "1609.TW", "1611.TW", "1618.TW"],
    "化學工業": ["1717.TW", "1722.TW", "1723.TW", "1712.TW", "1710.TW"],
    "生技醫療": ["6446.TW", "1795.TW", "6472.TW", "4147.TW", "1707.TW", "4743.TW"],
    "玻璃陶瓷": ["1802.TW", "1806.TW", "1809.TW"],
    "造紙工業": ["1907.TW", "1904.TW", "1909.TW", "1905.TW"],
    "鋼鐵工業": ["2002.TW", "2014.TW", "2027.TW", "2031.TW", "9958.TW", "2006.TW"],
    "橡膠工業": ["2105.TW", "2106.TW", "2101.TW", "2103.TW"],
    "汽車工業": ["2207.TW", "2201.TW", "2204.TW", "2206.TW", "2247.TW"],
    "半導體業": ["2330.TW", "2454.TW", "2303.TW", "3711.TW", "3661.TW", "3034.TW", "2379.TW", "2408.TW", "6415.TW", "2344.TW"],
    "電腦周邊": ["2382.TW", "2357.TW", "2324.TW", "3231.TW", "2376.TW", "2301.TW", "2395.TW", "4938.TW"],
    "光電業": ["3008.TW", "2409.TW", "3481.TW", "3406.TW", "2406.TW", "6116.TW"],
    "通信網路": ["2412.TW", "3045.TW", "4904.TW", "2345.TW", "6285.TW", "5388.TW"],
    "電子組件": ["2308.TW", "2327.TW", "3037.TW", "2383.TW", "3044.TW", "2368.TW"],
    "電子通路": ["3702.TW", "3036.TW", "2347.TW", "8112.TW", "5434.TW"],
    "資訊服務": ["6214.TW", "6183.TW", "2480.TW", "5403.TW"],
    "其他電子": ["2317.TW", "2474.TW", "2360.TW", "6139.TW", "2404.TW"],
    "建材營造": ["2542.TW", "2548.TW", "5534.TW", "5522.TW", "2501.TW", "2520.TW"],
    "航運業": ["2603.TW", "2609.TW", "2615.TW", "2610.TW", "2618.TW", "2633.TW"],
    "觀光餐旅": ["2707.TW", "2727.TW", "2731.TW", "2748.TW", "2704.TW"],
    "金融保險": ["2881.TW", "2882.TW", "2891.TW", "2886.TW", "2884.TW", "5880.TW", "2885.TW", "2892.TW", "2880.TW", "2883.TW"],
    "貿易百貨": ["2912.TW", "8454.TW", "2903.TW", "5904.TW"],
    "郵電燃氣": ["8908.TW", "8931.TW", "6505.TW"],
    "綠能環保": ["9930.TW", "6806.TW", "6869.TW", "3708.TW"],
    "數位雲端": ["6689.TW", "6173.TW", "6906.TW"],
    "運動休閒": ["9904.TW", "9910.TW", "9914.TW", "9921.TW", "1736.TW"],
    "居家生活": ["8464.TW", "9911.TW", "9934.TW"],
    "其他": ["9933.TW", "9907.TW", "9938.TW"],
    "ETF與公債": ["0050.TW", "006208.TW", "0056.TW", "00878.TW", "00919.TW", "00929.TW", "00679B.TW", "00687B.TW"]
}

# 美台連動映射
CORRELATION_MAP = {
    "NVDA": ["2330.TW", "2317.TW", "2382.TW", "3231.TW", "6669.TW"], 
    "TSM": ["2330.TW", "2303.TW", "3711.TW", "3661.TW"],            
    "AAPL": ["2330.TW", "2317.TW", "3008.TW", "3406.TW", "4938.TW"],
    "TSLA": ["2330.TW", "3019.TW", "2308.TW", "2421.TW"],           
    "AMD": ["2330.TW", "2376.TW", "3231.TW", "6669.TW"],            
    "MSFT": ["2330.TW", "2382.TW", "6669.TW"],                      
    "GOOGL": ["2330.TW", "2382.TW", "3231.TW"]                      
}

# --- 2. 側邊欄：全域配置 (避免重複 ID 錯誤) ---
st.sidebar.title("🛠️ 全域配置")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password", key="gemini_api_key")
auto_threshold = st.sidebar.slider("推薦門檻 (分)", 10, 100, 40)

with st.sidebar.expander("⚖️ 權重分配", expanded=True):
    w_rsi = st.slider("RSI 超賣", 0, 100, 30)
    w_ma = st.slider("MA 金叉", 0, 100, 20)
    w_vol = st.slider("劇烈波動", 0, 100, 15)
    w_news = st.slider("AI 資訊面權重", 0, 100, 35)

# --- 3. AI 分析核心 ---
def get_ai_score(target, context, mode="single"):
    if not api_key: return {"score": 50, "reason": "未填寫 API"}
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompts = {
            "single": f"分析{target}新聞，給予0-100分(50中立)。格式:{{'score':x, 'reason':''}}",
            "industry": f"分析{target}行業趨勢，給予景氣分(0-100)。格式:{{'score':x, 'reason':''}}",
            "impact": f"分析美股新聞對台股供應鏈{target}的影響。格式:{{'score':x, 'reason':''}}"
        }
        
        response = model.generate_content(f"{prompts[mode]}\n新聞內容：{context}")
        return json.loads(response.text.replace('```json', '').replace('```', '').strip())
    except: return {"score": 50, "reason": "AI 分析超時"}

# --- 4. 掃描邏輯 ---
if st.button("🚀 啟動全產業 AI 戰略分析"):
    if not api_key:
        st.error("請先在側邊欄輸入 API Key！")
    else:
        # A. 美股影響分析
        st.info("正在評估美股龍頭對台連動影響...")
        us_impact = {}
        for us_t, tw_list in CORRELATION_MAP.items():
            news = yf.Ticker(us_t).news[:2]
            res = get_ai_score(tw_list, news, mode="impact")
            for t in tw_list: us_impact[t] = res['score']

        # B. 產業掃描與熱力圖數據
        ind_data = []
        stock_results = []
        progress = st.progress(0)
        
        for idx, (ind_name, tickers) in enumerate(INDUSTRY_GROUPS.items()):
            # 取得行業景氣分
            ind_news = [n['title'] for t in tickers[:2] for n in yf.Ticker(t).news[:1]]
            ind_res = get_ai_score(ind_name, ind_news, mode="industry")
            ind_data.append({"產業": ind_name, "景氣分數": ind_res['score']})
            
            # 掃描個股
            for t in tickers[:3]:
                try:
                    df = yf.download(t, period="60d", progress=False, auto_adjust=True)
                    if df.empty: continue
                    # 技術指標
                    df['RSI'] = ta.rsi(df['Close'], length=14)
                    curr, prev = df.iloc[-1], df.iloc[-2]
                    
                    tech_s = 0
                    if curr['RSI'] < 35: tech_s += w_rsi
                    
                    # 整合資訊面 (美股影響 40% + 產業景氣 60%)
                    final_info = (us_impact.get(t, 50) * 0.4 + ind_res['score'] * 0.6)
                    info_weighted = (final_info - 50) / 50 * w_news
                    
                    total = tech_s + info_weighted
                    stock_results.append({
                        "代碼": t, "總分": round(total, 1), "現價": round(float(curr['Close']), 2),
                        "產業": ind_name, "AI評點": ind_res['reason']
                    })
                except: continue
            progress.progress((idx + 1) / len(INDUSTRY_GROUPS))

        # --- 5. 視覺化呈現 ---
        st.subheader("📊 全產業 AI 景氣熱力圖")
        fig = px.bar(pd.DataFrame(ind_data), x="產業", y="景氣分數", color="景氣分數", color_continuous_scale="RdYlGn")
        st.plotly_chart(fig, use_container_width=True)

        st.subheader("🏆 策略推薦標的")
        df_final = pd.DataFrame(stock_results).sort_values("總分", ascending=False)
        st.dataframe(df_final[df_final['總分'] >= auto_threshold], use_container_width=True)

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
