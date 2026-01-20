import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import plotly.express as px

# --- 1. 配置與完整產業資料 ---
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


# --- 2. 側邊欄：全域配置 (修復 Duplicate ID) ---
st.sidebar.title("🛠️ AI 戰略配置")
api_key = st.sidebar.text_input("輸入 Gemini API Key", type="password", key="main_key")

with st.sidebar.expander("⚖️ 權重分配", expanded=True):
    w_rsi = st.sidebar.slider("RSI 超賣權重", 0, 100, 30)
    w_news = st.sidebar.slider("AI 資訊分析權重", 0, 100, 70)

# --- 3. 強化的 AI 分析引擎 (避免 50 分卡死) ---
def get_ai_score(target, news_list):
    if not api_key: return {"score": 50, "reason": "未輸入 API"}
    try:
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        context = " ".join(news_list) if news_list else "暫無新聞"
        prompt = f"分析 {target} 近期新聞對股價影響：{context}。請評估利多程度 (0-100)。格式必須為 JSON: {{'score': 分數, 'reason': '一句話'}}"
        response = model.generate_content(prompt)
        # 清理字串，防止解析錯誤
        clean_json = response.text.replace('```json', '').replace('```', '').strip()
        data = json.loads(clean_json)
        return data
    except:
        return {"score": 50, "reason": "AI 分析失效"}

# --- 4. 執行按鈕 ---
if st.button("🚀 啟動全產業 AI 戰略掃描"):
    if not api_key:
        st.error("請先填入 API Key！")
    else:
        all_results = []
        heat_results = []
        us_impact = {}
        
        # Step 1: 美股分析
        st.info("Step 1: 正在評估美股龍頭對台連動影響...")
        for us_t, tw_list in CORRELATION_MAP.items():
            try:
                raw_n = yf.Ticker(us_t).news
                titles = [n['title'] for n in raw_n[:2]] if raw_n else []
                res = get_ai_score(us_t, titles)
                for t in tw_list: us_impact[t] = res['score']
            except: pass

        # Step 2: 產業分析與個股掃描
        st.info("Step 2: 正在執行 34 個產業分析...")
        progress = st.progress(0)
        
        for i, (ind_name, tickers) in enumerate(INDUSTRY_GROUPS.items()):
            # 安全抓取產業新聞，解決 KeyError (圖 6af145)
            ind_news = []
            for t in tickers[:2]:
                try:
                    raw_n = yf.Ticker(t).news
                    if raw_n: ind_news.append(raw_n[0]['title'])
                except: continue
            
            ind_res = get_ai_score(ind_name, ind_news)
            heat_results.append({"產業": ind_name, "景氣分數": ind_res['score']})
            
            # 掃描該產業內的個股
            for t in tickers:
                try:
                    df = yf.download(t, period="60d", progress=False, auto_adjust=True)
                    if df.empty: continue
                    # 計算 RSI
                    df['RSI'] = ta.rsi(df['Close'], length=14)
                    curr_rsi = df['RSI'].iloc[-1]
                    
                    # 綜合評分邏輯 (修復圖 6af50b 的括號錯誤)
                    ai_val = (us_impact.get(t, 50) * 0.4 + ind_res['score'] * 0.6)
                    info_score = ((ai_val - 50) / 50) * w_news
                    tech_score = w_rsi if curr_rsi < 35 else 0
                    
                    all_results.append({
                        "產業": ind_name, "代碼": t, "總分": round(tech_score + info_score, 1),
                        "現價": round(float(df['Close'].iloc[-1]), 2), "AI短評": ind_res['reason']
                    })
                except: continue
            progress.progress((i + 1) / len(INDUSTRY_GROUPS))

        # --- 5. 確保資料完整才渲染介面 ---
        st.subheader("📊 全產業 AI 景氣分布圖")
        if heat_results:
            df_heat = pd.DataFrame(heat_results)
            fig = px.bar(df_heat, x="產業", y="景氣分數", color="景氣分數", 
                         color_continuous_scale="RdYlGn", text_auto=True)
            st.plotly_chart(fig, use_container_width=True)

        st.subheader("🏆 策略優選標的")
        if all_results:
            df_final = pd.DataFrame(all_results).sort_values("總分", ascending=False)
            st.dataframe(df_final, use_container_width=True)
        else:
            st.warning("掃描完成，但沒有符合權重分數的標的。請檢查權重分配。")
