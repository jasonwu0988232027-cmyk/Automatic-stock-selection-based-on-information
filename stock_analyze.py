import streamlit as st
import yfinance as yf
import pandas as pd
import google.generativeai as genai
import json

# --- 1. 擴展映射表：美台龍頭連動 ---
# 格式：美股代碼 : [受影響的台股代碼清單]
# --- 產業前 10 龍頭企業分類清單 (INDUSTRY_GROUPS) ---
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

# --- 美台龍頭連動映射表 (CORRELATION_MAP) ---
CORRELATION_MAP = {
    "NVDA": ["2330.TW", "2317.TW", "2382.TW", "3231.TW", "6669.TW"], # AI 伺服器鏈
    "TSM": ["2330.TW", "2303.TW", "3711.TW", "3661.TW"],           # 半導體設備與代工
    "AAPL": ["2330.TW", "2317.TW", "3008.TW", "3406.TW", "4938.TW"],# 蘋果供應鏈
    "TSLA": ["2330.TW", "3019.TW", "2308.TW", "2421.TW"],           # 車用與電力
    "AMD": ["2330.TW", "2376.TW", "3231.TW", "6669.TW"],            # 高效能運算
    "MSFT": ["2330.TW", "2382.TW", "6669.TW"],                      # 雲端資料中心
    "GOOGL": ["2330.TW", "2382.TW", "3231.TW"]                      # 雲端硬體
}

# --- 2. 強化版 Gemini 分析函數 ---
def gemini_strategic_analysis(target_name, news_data, mode="single"):
    """
    mode "single": 個股分析
    mode "industry": 行業趨勢分析
    mode "us_impact": 美股對台股影響評估
    """
    genai.configure(api_key="YOUR_GEMINI_API_KEY")
    model = genai.GenerativeModel('gemini-1.5-flash')
    
    prompts = {
        "single": f"分析{target_name}新聞，給予0-100分(50中立)並註明原因。格式:{{'score':x, 'reason':''}}",
        "industry": f"分析{target_name}行業近期前10大新聞，評估整體產業景氣得分(0-100)。",
        "us_impact": f"分析美股龍頭新聞：{news_data}，評估其對台灣關聯企業{target_name}的『利多連動程度』(0-100)。"
    }
    
    try:
        response = model.generate_content(f"{prompts[mode]}\n新聞內容：{news_data}")
        res_text = response.text.replace('```json', '').replace('```', '').strip()
        return json.loads(res_text)
    except:
        return {"score": 50, "reason": "分析超時"}

# --- 3. 掃描邏輯優化 ---
def smart_scan(weights):
    results = []
    
    # A. 先抓取美股龍頭新聞，建立「今日外部環境分」
    us_impact_scores = {}
    for us_ticker, tw_list in CORRELATION_MAP.items():
        us_news = yf.Ticker(us_ticker).news[:2]
        impact = gemini_strategic_analysis(tw_list, us_news, mode="us_impact")
        for tw_id in tw_list:
            us_impact_scores[tw_id] = impact['score']

    # B. 執行台股掃描
    for ticker, name in STOCK_DICT.items():
        stock = yf.Ticker(ticker)
        df = stock.history(period="5d")
        if df.empty: continue
        
        # 1. 偵測異常漲跌幅 (原因查找)
        last_change = ((df['Close'].iloc[-1] - df['Close'].iloc[-2]) / df['Close'].iloc[-2]) * 100
        extra_info_score = 0
        if abs(last_change) > 7.0:
            # 觸發 Gemini 專項調查
            investigation = gemini_strategic_analysis(name, stock.news[:3], mode="single")
            extra_info_score = investigation['score']
        
        # 2. 整合美股權重與個股權重
        base_ai_score, _ = gemini_strategic_analysis(name, stock.news[:2], mode="single")
        us_bonus = us_impact_scores.get(ticker, 50) # 若無美股連動則中立
        
        # 最終資訊面加權 = (個股AI + 美股連動AI + 異常調查分) / 權重比
        final_info_val = (base_ai_score * 0.4 + us_bonus * 0.4 + (extra_info_score if extra_info_score !=0 else 50) * 0.2)
        
        # (結合您原本的 RSI/MA 邏輯...)
        # score = tech_score + (final_info_val - 50) / 50 * weights['news']
        
        # 存入結果並顯示...
