import streamlit as st
import yfinance as yf
from datetime import datetime

st.set_page_config(page_title="股市新聞搜尋器", layout="wide")

# 加入快取功能，TTL 設定為 600 秒（10分鐘刷新一次），避免頻繁請求
@st.cache_data(ttl=600)
def get_stock_news(ticker_str):
    stock = yf.Ticker(ticker_str)
    # 獲取新聞
    return stock.news, stock.info

st.title("📈 股票代碼新聞搜尋 (優化版)")
st.markdown("輸入股票代碼並按下 Enter。快取功能已啟用，可減少 `Too Many Requests` 錯誤。")

ticker_input = st.sidebar.text_input("輸入股票代碼", value="AAPL").upper()

if ticker_input:
    try:
        # 呼叫帶有快取的函式
        news_list, info = get_stock_news(ticker_input)
        
        st.header(f"{info.get('longName', ticker_input)} ({ticker_input})")
        
        if not news_list:
            st.warning(f"找不到關於 {ticker_input} 的相關新聞。")
        else:
            st.subheader("最新相關新聞")
            for article in news_list:
                with st.expander(f"📌 {article['title']}"):
                    pub_time = datetime.fromtimestamp(article['providerPublishTime']).strftime('%Y-%m-%d %H:%M:%S')
                    st.write(f"**來源:** {article['publisher']}")
                    st.write(f"**發佈時間:** {pub_time}")
                    st.markdown(f"[閱讀全文]({article['link']})")
                    
    except Exception as e:
        st.error(f"搜尋出錯：{e}")
        st.info("💡 提示：如果持續出現 Rate Limited，請嘗試更換 IP（例如切換手機熱點）或稍等 15 分鐘再試。")
