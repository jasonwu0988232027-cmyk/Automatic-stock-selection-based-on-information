import streamlit as st
import yfinance as yf
import pandas as pd
import pandas_ta as ta
import google.generativeai as genai
import json
import time

# --- 網頁配置 ---
st.set_page_config(page_title="AI 產業權值百科 v15", layout="wide")

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

# 平鋪所有股票代碼以便搜尋
STOCK_DICT = {}
for industry, tickers in INDUSTRY_GROUPS.items():
    for t in tickers: STOCK_DICT[t] = t # 暫以代碼當名稱，或可手動補回原中文名

# --- 2. Gemini AI 分析邏輯 ---
def gemini_strategic_analysis(target_name, news_data, mode="single"):
    """ AI 分析函數 """
    try:
        api_key = st.sidebar.text_input("Gemini API Key", type="password")
        if not api_key: return {"score": 50, "reason": "未輸入 API Key"}
        
        genai.configure(api_key=api_key)
        model = genai.GenerativeModel('gemini-1.5-flash')
        
        prompts = {
            "single": f"分析 {target_name} 新聞，給予 0-100 分 (50 中立) 並註明原因。格式: {{'score':x, 'reason':''}}",
            "us_impact": f"分析美股新聞：{news_data}，評估其對台股關聯企業 {target_name} 的『利多連動程度』(0-100)。格式: {{'score':x, 'reason':''}}"
        }
        
        response = model.generate_content(f"{prompts.get(mode, prompts['single'])}\n新聞內容：{news_data}")
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(res_text)
    except Exception as e:
        return {"score": 50, "reason": f"AI 異常: {str(e)}"}

# --- 3. 核心掃描邏輯 ---
def analyze_stock(ticker, weights, us_impact_score=50):
    try:
        df = yf.download(ticker, period="60d", interval="1d", progress=False, auto_adjust=True)
        if df.empty or len(df) < 20: return None
        if isinstance(df.columns, pd.MultiIndex): df.columns = df.columns.get_level_values(0)

        # A. 技術指標
        df['RSI'] = ta.rsi(df['Close'], length=14)
        df['MA5'] = ta.sma(df['Close'], length=5)
        df['MA10'] = ta.sma(df['Close'], length=10)
        curr, prev = df.iloc[-1], df.iloc[-2]
        
        tech_score = 0
        reasons = []
        
        if float(curr['RSI']) < 30: tech_score += weights['rsi']; reasons.append("RSI超賣")
        if float(prev['MA5']) < float(prev['MA10']) and float(curr['MA5']) > float(curr['MA10']):
            tech_score += weights['ma']; reasons.append("MA金叉")
        
        last_change = ((curr['Close'] - prev['Close']) / prev['Close']) * 100
        if abs(last_change) > 7.0:
            tech_score += weights['vol']; reasons.append(f"劇烈波動({round(last_change,1)}%)")
            # 異常漲跌幅調查
            investigation = gemini_strategic_analysis(ticker, yf.Ticker(ticker).news[:2], mode="single")
            extra_info_score = investigation['score']
        else:
            extra_info_score = 50

        if float(curr['Volume']) > df['Volume'].mean() * 2:
            tech_score += weights['vxx']; reasons.append("爆量")

        # B. 資訊面 AI 加權評分
        base_ai = gemini_strategic_analysis(ticker, yf.Ticker(ticker).news[:1], mode="single")
        final_info_val = (base_ai['score'] * 0.4 + us_impact_score * 0.4 + extra_info_score * 0.2)
        
        # 資訊面分數轉換：超過 50 加分，低於 50 扣分
        info_weight_score = (final_info_val - 50) / 50 * weights['news']
        total_score = tech_score + info_weight_score

        if total_score > 0:
            return {
                "名稱": ticker, "總分": round(total_score, 1), "現價": round(float(curr['Close']), 2),
                "漲跌幅": f"{round(last_change, 2)}%", "訊號": " | ".join(reasons), "AI評點": base_ai['reason']
            }
    except: return None

# --- 4. Streamlit 介面 ---
st.title("🏆 AI 戰略產業掃描系統")

with st.sidebar:
    st.header("權重分配")
    w_rsi = st.slider("RSI 超賣", 0, 100, 30)
    w_ma = st.slider("MA 金叉", 0, 100, 20)
    w_vol = st.slider("劇烈波動", 0, 100, 15)
    w_vxx = st.slider("成交爆量", 0, 100, 10)
    w_news = st.slider("AI 資訊面權重", 0, 100, 25)
    threshold = st.slider("顯示門檻分數", 0, 150, 40)

if st.button("🚀 啟動全產業戰略掃描"):
    # A. 獲取外部美股環境連動分
    st.info("正在分析美股龍頭對台連動影響...")
    us_impact_results = {}
    for us_t, tw_list in CORRELATION_MAP.items():
        try:
            us_news = yf.Ticker(us_t).news[:2]
            res = gemini_strategic_analysis(str(tw_list), str(us_news), mode="us_impact")
            for tw_id in tw_list: us_impact_results[tw_id] = res['score']
        except: pass

    # B. 執行台股掃描
    results = []
    all_tickers = [t for tickers in INDUSTRY_GROUPS.values() for t in tickers]
    progress_bar = st.progress(0)
    
    for idx, t in enumerate(all_tickers):
        impact_s = us_impact_results.get(t, 50)
        res = analyze_stock(t, {'rsi':w_rsi, 'ma':w_ma, 'vol':w_vol, 'vxx':w_vxx, 'news':w_news}, impact_s)
        if res: results.append(res)
        progress_bar.progress((idx + 1) / len(all_tickers))
        time.sleep(0.5) # 防止 API 頻率限制

    if results:
        df_final = pd.DataFrame(results).sort_values("總分", ascending=False)
        st.success("掃描完成！")
        st.dataframe(df_final[df_final['總分'] >= threshold], use_container_width=True)
    else:
        st.warning("未找到符合條件的股票。")
