import pandas as pd
import yfinance as yf
import requests
import streamlit as st

# 設定頁面標題
st.set_page_config(page_title="台股熱門動能掃描器", layout="wide")

class StockPoolManagerV2:
    def __init__(self):
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    @st.cache_data(ttl=3600) # 快取 1 小時，避免頻繁爬蟲被擋
    def get_hot_stocks(_self, limit=100):
        hot_tickers = []
        try:
            url = "https://tw.stock.yahoo.com/rank/turnover?exchange=TAI" 
            r = requests.get(url, headers=_self.headers)
            dfs = pd.read_html(r.text)
            df = dfs[0]
            
            target_col = None
            for i, col_name in enumerate(df.columns):
                if '股' in str(col_name) or '名' in str(col_name):
                    target_col = i
                    break
            
            if target_col is None: target_col = 1 
            
            count = 0
            for item in df.iloc[:, target_col]:
                item_str = str(item).strip()
                parts = item_str.split(' ')
                ticker = parts[0]
                if ticker.isdigit() and len(ticker) == 4:
                    hot_tickers.append(f"{ticker}.TW")
                    count += 1
                if count >= limit:
                    break
            return hot_tickers, "Success"

        except Exception as e:
            return _self._get_fallback_list(limit), f"Error: {e}"

    def _get_fallback_list(self, limit):
        fallback = [
            "2330.TW", "2454.TW", "2317.TW", "2303.TW", "2308.TW", "2382.TW", "3231.TW", "3443.TW", "3661.TW", "3035.TW",
            "2376.TW", "2356.TW", "6669.TW", "3017.TW", "3324.TW", "2421.TW", "3037.TW", "2368.TW", "2449.TW", "6271.TW",
            "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "1513.TW", "1519.TW", "1504.TW", "1605.TW", "2002.TW"
        ]
        return fallback[:limit]

    @st.cache_data(ttl=3600)
    def download_data_batch(_self, tickers):
        # 使用 threads=True 加速下載
        data = yf.download(tickers, period="1y", group_by='ticker', auto_adjust=True, threads=True) 
        if data.empty:
            return None
        data = data.dropna(axis=1, how='all')
        return data

# --- Streamlit UI 介面 ---
st.title("🚀 台股熱門掃描器 V2")
st.sidebar.header("設定")
stock_limit = st.sidebar.slider("抓取熱門股數量", 10, 100, 50)

manager = StockPoolManagerV2()

if st.button("開始掃描市場"):
    with st.spinner(f"正在從 Yahoo 財經抓取成交值前 {stock_limit} 名..."):
        hot_list, status = manager.get_hot_stocks(limit=stock_limit)
        
        if "Error" in status:
            st.warning(f"🛡️ 爬蟲遭遇亂流，已啟動戰備清單 (Fallback) 模式。")
        else:
            st.success(f"✅ 成功鎖定 {len(hot_list)} 檔熱門潛力股！")
        
        st.write("目前追蹤清單：", ", ".join(hot_list[:15]) + " ...")

    with st.spinner("📥 正在下載歷史數據 (可能需要 30 秒)..."):
        market_data = manager.download_data_batch(hot_list)

    if market_data is not None and not market_data.empty:
        st.divider()
        st.subheader("📊 數據預覽")
        
        # 顯示龍頭股數據
        first_stock = hot_list[0]
        try:
            # 判斷 yfinance 回傳的多索引結構
            if len(hot_list) > 1:
                stock_df = market_data[first_stock].tail(10)
            else:
                stock_df = market_data.tail(10)
            
            st.write(f"最近 10 筆數據： {first_stock}")
            st.dataframe(stock_df, use_container_width=True)
            
            # 簡易圖表展示
            st.line_chart(stock_df['Close'])
            
        except Exception as e:
            st.error(f"解析數據時發生錯誤: {e}")
            st.write(market_data.head())
    else:
        st.error("無法取得數據，請稍後再試。")

else:
    st.info("請點擊「開始掃描」按鈕來執行程式。")
