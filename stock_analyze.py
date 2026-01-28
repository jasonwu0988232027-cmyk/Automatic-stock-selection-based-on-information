import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

# --- 安全與基礎配置 ---
urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股指標排行榜", layout="wide")

@st.cache_data(ttl=3600) # 緩存 1 小時，避免頻繁請求證交所
def get_safe_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    headers = {
        'User-Agent': 'Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36'
    }
    try:
        response = requests.get(url, headers=headers, timeout=15, verify=False)
        response.encoding = 'big5'
        # 使用多種解析引擎重試
        try:
            tables = pd.read_html(response.text, flavor='lxml')
        except:
            tables = pd.read_html(response.text, flavor='html5lib')
            
        df = tables[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        # 篩選標準 4 碼台股
        list_tickers = []
        for item in df['有價證券代號及名稱']:
            code = item.split("  ")[0].strip()
            if code.isdigit() and len(code) == 4:
                list_tickers.append(f"{code}.TW")
        return list_tickers
    except Exception as e:
        st.error(f"無法獲取名單: {e}")
        return []

def fetch_data_robust(tickers):
    all_results = []
    batch_size = 15 # 縮小批次提高穩定性
    p_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"📊 正在分析指標: {i} / {len(tickers)} ...")
        
        try:
            # 請求 5 天數據以防假日無數據
            df = yf.download(batch, period="5d", group_by='ticker', threads=False, timeout=20)
            
            for t in batch:
                try:
                    # 判斷多股票下載後的結構
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        price = float(last['Close'])
                        volume = float(last['Volume'])
                        # 成交值指標 (億)
                        val = round((price * volume) / 100_000_000, 2)
                        
                        if val > 0:
                            all_results.append({
                                "股票代號": t,
                                "收盤價": round(price, 2),
                                "成交量(張)": int(volume // 1000),
                                "成交金額(億)": val,
                                "成交值指標": val
                            })
                except: continue
        except:
            st.warning(f"批次 {i} 抓取超時，自動跳過...")
            
        time.sleep(random.uniform(1.2, 2.5)) # 隨機延遲預防封鎖
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
        
    status_text.text("✅ 分析完成")
    return pd.DataFrame(all_results)

# --- Streamlit 主介面 ---
st.title("📊 台股成交值指標 Top 100 排行榜")
st.info("本系統會掃描全市場，並依據「成交值指標」由高至低排列前 100 名。")

if 'last_run' not in st.session_state:
    st.session_state.last_run = 0

time_diff = time.time() - st.session_state.last_run

if st.button("🚀 開始執行全市場篩選", type="primary"):
    if time_diff < 300:
        st.error(f"🛑 系統冷卻中，請等待 {int(300 - time_diff)} 秒。")
    else:
        st.session_state.last_run = time.time()
        
        with st.status("正在獲取台股清單...", expanded=False):
            all_list = get_safe_tickers()
        
        if all_list:
            st.write(f"🔍 成功獲取 {len(all_list)} 隻股票，開始計算指標...")
            final_df = fetch_data_robust(all_list)
            
            if not final_df.empty:
                # 關鍵：依照指標排序並取前 100 名
                top_100 = final_df.sort_values("成交值指標", ascending=False).head(100).reset_index(drop=True)
                top_100.index += 1
                
                st.subheader(f"🏆 資金熱點 Top 100 ({datetime.now().strftime('%Y-%m-%d')})")
                
                # 格式化顯示
                try:
                    styled = top_100.style.format({
                        "收盤價": "{:.2f}", 
                        "成交金額(億)": "{:.2f}", 
                        "成交值指標": "{:.2f}"
                    }).background_gradient(subset=['成交值指標'], cmap='YlOrRd')
                    st.dataframe(styled, use_container_width=True)
                except:
                    st.dataframe(top_100, use_container_width=True)
                
                csv = top_100.to_csv(index=False).encode('utf-8-sig')
                st.download_button("📥 下載排行榜 CSV", data=csv, file_name="TW_Stock_Indicator.csv")
            else:
                st.error("掃描結果為空，可能是連線被 Yahoo 阻斷，請稍後再試。")
        else:
            st.error("名單獲取失敗，請檢查證交所連線狀態。")

st.divider()
st.caption("備註：所有數據均四捨五入至小數點第 2 位。")
