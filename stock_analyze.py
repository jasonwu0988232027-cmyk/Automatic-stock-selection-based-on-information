import streamlit as st
import yfinance as yf
import pandas as pd
import time
import random
import requests
import urllib3
from datetime import datetime

urllib3.disable_warnings(urllib3.exceptions.InsecureRequestWarning)
st.set_page_config(page_title="台股成交值指標 Top 100", layout="wide")

@st.cache_data(ttl=86400)
def get_all_tickers():
    url = "https://isin.twse.com.tw/isin/C_public.jsp?strMode=2"
    try:
        res = requests.get(url, headers={'User-Agent': 'Mozilla/5.0'}, verify=False, timeout=15)
        res.encoding = 'big5'
        df = pd.read_html(res.text)[0]
        df.columns = df.iloc[0]
        df = df[df['有價證券代號及名稱'].str.contains("  ", na=False)]
        return [f"{t.split('  ')[0]}.TW" for t in df['有價證券代號及名稱'] if len(t.split('  ')[0]) == 4]
    except: return ["2330.TW", "2317.TW", "2454.TW"]

def fetch_data(tickers):
    all_res = []
    batch_size = 20
    p_bar = st.progress(0)
    status_text = st.empty()
    
    for i in range(0, len(tickers), batch_size):
        batch = tickers[i : i + batch_size]
        status_text.text(f"⏳ 正在篩選全市場資金標的: {i} / {len(tickers)}...")
        try:
            df = yf.download(batch, period="5d", group_by='ticker', threads=False)
            for t in batch:
                try:
                    t_df = df[t].dropna() if isinstance(df.columns, pd.MultiIndex) else df.dropna()
                    if not t_df.empty:
                        last = t_df.iloc[-1]
                        p, v = float(last['Close']), float(last['Volume'])
                        val = round((p * v) / 100_000_000, 2)
                        if val > 0:
                            all_res.append({
                                "股票代號": t, 
                                "收盤價": round(p, 2), 
                                "成交量(張)": int(v // 1000), 
                                "成交金額(億)": val, 
                                "成交值指標": val
                            })
                except: continue
        except: pass
        time.sleep(random.uniform(1.0, 2.0))
        p_bar.progress(min((i + batch_size) / len(tickers), 1.0))
    
    status_text.text("✅ 全市場指標計算完畢")
    return pd.DataFrame(all_res)

# --- UI 介面 ---
st.title("📊 台股成交值指標 Top 100 排行榜")
st.markdown("本表依據 **[成交值指標]** 由高至低排序，挑選市場資金最集中的前 100 名。")

if 'last_run' not in st.session_state: st.session_state.last_run = 0
time_diff = time.time() - st.session_state.last_run

if st.button("🚀 執行全市場掃描", type="primary"):
    if time_diff < 300:
        st.error(f"🛑 系統冷卻中，請等待 {int(300 - time_diff)} 秒。")
    else:
        st.session_state.last_run = time.time()
        tickers = get_all_tickers()
        df_raw = fetch_data(tickers)
        
        if not df_raw.empty:
            # 關鍵步驟：依照成交值指標進行排序並取前 100 名
            top_100 = df_raw.sort_values("成交值指標", ascending=False).head(100).reset_index(drop=True)
            top_100.index += 1 # 排名從 1 開始
            
            st.subheader(f"🏆 資金熱點 Top 100 ({datetime.now().strftime('%Y-%m-%d')})")
            
            # 格式化所有數值欄位為兩位小數並加上漸層色
            cols_to_format = ["收盤價", "成交金額(億)", "成交值指標"]
            try:
                styled_df = top_100.style.format({c: "{:.2f}" for c in cols_to_format})\
                                       .background_gradient(subset=['成交值指標'], cmap='YlOrRd')
                st.dataframe(styled_df, use_container_width=True)
            except:
                st.dataframe(top_100, use_container_width=True)
                
            # 提供 CSV 下載
            csv_data = top_100.to_csv(index=False).encode('utf-8-sig')
            st.download_button("📥 下載成交值指標報表", data=csv_data, file_name="Stock_Top100_Indicator.csv")
        else:
            st.error("無法獲取數據，請確認網路連線。")

st.divider()
st.caption("註：成交值指標計算方式為 (成交單價 × 當日總成交股數) / 10^8，單位為億元。")
