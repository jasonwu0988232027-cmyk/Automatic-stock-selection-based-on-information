import streamlit as st
import yfinance as yf
from datetime import datetime

# 設定網頁標題
st.set_page_config(page_title="股市新聞搜尋器", layout="wide")

st.title("📈 股票代碼新聞搜尋")
st.markdown("輸入股票代碼（如：`AAPL`, `TSLA`, `2330.TW`）來獲取相關新聞。")

# 側邊欄輸入
ticker_input = st.sidebar.text_input("輸入股票代碼", value="AAPL").upper()

if ticker_input:
    try:
        # 初始化 Ticker 物件
        stock = yf.Ticker(ticker_input)
        
        # 顯示公司基本資訊（選填）
        info = stock.info
        st.header(f"{info.get('longName', ticker_input)} ({ticker_input})")
        
        # 獲取新聞
        news_list = stock.news
        
        if not news_list:
            st.warning(f"找不到關於 {ticker_input} 的相關新聞。")
        else:
            st.subheader("最新相關新聞")
            
            for article in news_list:
                with st.expander(f"📌 {article['title']}"):
                    # 格式化時間
                    pub_time = datetime.fromtimestamp(article['providerPublishTime']).strftime('%Y-%m-%d %H:%M:%S')
                    
                    st.write(f"**來源:** {article['publisher']}")
                    st.write(f"**發佈時間:** {pub_time}")
                    st.write(f"**摘要:** {article.get('summary', '無摘要')}")
                    st.markdown(f"[閱讀全文]({article['link']})")
                    
    except Exception as e:
        st.error(f"搜尋出錯：請確認代碼是否正確。錯誤訊息: {e}")

else:
    st.info("請在側邊欄輸入股票代碼開始搜尋。")
