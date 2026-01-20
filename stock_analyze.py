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
    # 水泥工業
    "1101.TW": "台泥", "1102.TW": "亞泥", "1108.TW": "幸福", "1109.TW": "信大", "1110.TW": "東泥",
    # 食品工業
    "1216.TW": "統一", "1210.TW": "大成", "1215.TW": "卜蜂", "1227.TW": "佳格", "1229.TW": "聯華", "1231.TW": "聯華食",
    # 塑膠工業
    "1301.TW": "台塑", "1303.TW": "南亞", "1326.TW": "台化", "1304.TW": "台聚", "1308.TW": "亞聚", "1309.TW": "台達化",
    # 紡織纖維
    "1402.TW": "遠東新", "1476.TW": "儒鴻", "1477.TW": "聚陽", "1409.TW": "新纖", "1444.TW": "力麗",
    # 電器機械
    "1503.TW": "士電", "1504.TW": "東元", "1513.TW": "中興電", "1519.TW": "華城", "1560.TW": "中砂", "1590.TW": "亞德客-KY",
    # 電器電纜
    "1605.TW": "華新", "1608.TW": "華榮", "1609.TW": "大亞", "1611.TW": "中電", "1618.TW": "合機",
    # 化學工業
    "1717.TW": "長興", "1722.TW": "台肥", "1723.TW": "中碳", "1712.TW": "興農", "1710.TW": "東聯",
    # 生技醫療
    "6446.TW": "藥華藥", "1795.TW": "美時", "6472.TW": "保瑞", "4147.TW": "龍燈-KY", "1707.TW": "葡萄王", "4743.TW": "合一",
    # 玻璃陶瓷
    "1802.TW": "台玻", "1806.TW": "冠軍", "1809.TW": "中釉",
    # 造紙工業
    "1907.TW": "永豐餘", "1904.TW": "正隆", "1909.TW": "榮成", "1905.TW": "華紙",
    # 鋼鐵工業
    "2002.TW": "中鋼", "2014.TW": "中鴻", "2027.TW": "大鴻", "2031.TW": "新光鋼", "9958.TW": "世紀鋼", "2006.TW": "東和鋼鐵",
    # 橡膠工業
    "2105.TW": "正新", "2106.TW": "建大", "2101.TW": "南港", "2103.TW": "台橡",
    # 汽車工業
    "2207.TW": "和泰車", "2201.TW": "裕隆", "2204.TW": "中華", "2206.TW": "三陽工業", "2247.TW": "汎德永業",
    # 半導體業
    "2330.TW": "台積電", "2454.TW": "聯發科", "2303.TW": "聯電", "3711.TW": "日月光投控", "3661.TW": "世芯-KY", "3034.TW": "聯詠", "2379.TW": "瑞昱", "2408.TW": "南亞科", "6415.TW": "矽力*-KY", "2344.TW": "華邦電",
    # 電腦周邊
    "2382.TW": "廣達", "2357.TW": "華碩", "2324.TW": "仁寶", "3231.TW": "緯創", "2376.TW": "技嘉", "2301.TW": "光寶科", "2395.TW": "研華", "4938.TW": "和碩",
    # 光電業
    "3008.TW": "大立光", "2409.TW": "友達", "3481.TW": "群創", "3406.TW": "玉晶光", "2406.TW": "國碩", "6116.TW": "彩晶",
    # 通信網路
    "2412.TW": "中華電", "3045.TW": "台灣大", "4904.TW": "遠傳", "2345.TW": "智邦", "6285.TW": "啟碁", "5388.TW": "中磊",
    # 電子組件
    "2308.TW": "台達電", "2327.TW": "國巨", "3037.TW": "欣興", "2383.TW": "台光電", "3044.TW": "健鼎", "2368.TW": "金像電",
    # 電子通路
    "3702.TW": "大聯大", "3036.TW": "文曄", "2347.TW": "聯強", "8112.TW": "至上", "5434.TW": "崇越",
    # 資訊服務
    "6214.TW": "精誠", "6183.TW": "關貿", "2480.TW": "敦陽科", "5403.TW": "中菲",
    # 其他電子
    "2317.TW": "鴻海", "2474.TW": "可成", "2360.TW": "致茂", "6139.TW": "亞翔", "2404.TW": "漢唐",
    # 建材營造
    "2542.TW": "興富發", "2548.TW": "華固", "5534.TW": "長虹", "5522.TW": "遠雄", "2501.TW": "國建", "2520.TW": "冠德",
    # 航運業
    "2603.TW": "長榮", "2609.TW": "陽明", "2615.TW": "萬海", "2610.TW": "華航", "2618.TW": "長榮航", "2633.TW": "台灣高鐵",
    # 觀光餐旅
    "2707.TW": "晶華", "2727.TW": "王品", "2731.TW": "雄獅", "2748.TW": "雲品", "2704.TW": "國賓",
    # 金融保險
    "2881.TW": "富邦金", "2882.TW": "國泰金", "2891.TW": "中信金", "2886.TW": "兆豐金", "2884.TW": "玉山金", "5880.TW": "合庫金", "2885.TW": "元大金", "2892.TW": "第一金", "2880.TW": "華南金", "2883.TW": "開發金",
    # 貿易百貨
    "2912.TW": "統一超", "8454.TW": "富邦媒", "2903.TW": "遠百", "5904.TW": "寶雅",
    # 郵電燃氣
    "8908.TW": "欣雄", "8931.TW": "欣高", "6505.TW": "台塑化",
    # 綠能環保
    "9930.TW": "中聯資源", "6806.TW": "森崴能源", "6869.TW": "雲豹能源", "3708.TW": "上緯投控",
    # 數位雲端
    "6689.TW": "伊雲谷", "6173.TW": "浪凡", "6906.TW": "現觀科",
    # 運動休閒
    "9904.TW": "寶成", "9910.TW": "豐泰", "9914.TW": "美利達", "9921.TW": "巨大", "1736.TW": "喬山",
    # 居家生活
    "8464.TW": "億豐", "9911.TW": "櫻花", "9934.TW": "成霖",
    # 其他
    "9933.TW": "中鼎", "9907.TW": "統一實", "9938.TW": "百和",
    # ETF / 反向 / 槓桿
    "0050.TW": "元大台灣50", "006208.TW": "富邦台50", "0056.TW": "元大高股息", "00878.TW": "國泰永續高股息", 
    "00919.TW": "群益台灣精選高息", "00929.TW": "復華台灣科技優息", "00632R.TW": "元大台灣50反1", "00631L.TW": "元大台灣50正2",
    # 政府公債 ETF
    "00679B.TW": "元大美債20年", "00687B.TW": "國泰美債20年", "00795B.TW": "中信美國公債20年", "00696B.TW": "富邦美債20年",
    # 美股龍頭
    "AAPL": "蘋果", "NVDA": "輝達", "TSLA": "特斯拉", "AMD": "超微", "MSFT": "微軟", "GOOGL": "谷歌", "META": "臉書", "AMZN": "亞馬遜"
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
