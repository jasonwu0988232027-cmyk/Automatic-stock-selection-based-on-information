!pip install yfinance pandas requests lxml

import pandas as pd
import yfinance as yf
import requests

class StockPoolManagerV2:
    def __init__(self):
        # 偽裝成一般瀏覽器，避免被網站擋
        self.headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/91.0.4472.124 Safari/537.36"
        }

    def get_hot_stocks(self, limit=100):
        print(f"🚀 正在掃描市場成交重心，目標獲取前 {limit} 檔熱門股...")
        
        hot_tickers = []
        
        try:
            # 抓取 Yahoo 股市「成交值」排行榜
            # 這裡我們嘗試抓取列表
            url = "https://tw.stock.yahoo.com/rank/turnover?exchange=TAI" 
            r = requests.get(url, headers=self.headers)
            
            # 讀取網頁表格
            dfs = pd.read_html(r.text)
            df = dfs[0] # 抓取第一個表格
            
            # --- 智慧清洗邏輯 ---
            # Yahoo 的欄位通常是 "股名 2330", 需要拆解
            # 我們遍歷每一列，嘗試提取代號
            
            # 找出包含股名的那個欄位 (通常是第二欄，索引 1，或是標題有'股號'的)
            # 這裡做一個動態偵測，比較保險
            target_col = None
            for i, col_name in enumerate(df.columns):
                if '股' in str(col_name) or '名' in str(col_name):
                    target_col = i
                    break
            
            if target_col is None: target_col = 1 # 預設第二欄
            
            count = 0
            for item in df.iloc[:, target_col]:
                item_str = str(item).strip()
                
                # 嘗試切割出代號 (例如 "2330 台積電" -> "2330")
                # 或是有些格式是純代號
                parts = item_str.split(' ')
                ticker = parts[0]
                
                # 過濾邏輯：

                if ticker.isdigit() and len(ticker) == 4:
                    hot_tickers.append(f"{ticker}.TW")
                    count += 1
                
                if count >= limit:
                    break
            
            print(f"✅ 成功鎖定 {len(hot_tickers)} 檔熱門潛力股！")
            
            # 如果抓到的不夠多 (Yahoo 網頁可能只顯示 30 筆)，我們就用多少算多少
            if len(hot_tickers) < limit:
                print(f"⚠️ 注意：網頁僅提供前 {len(hot_tickers)} 名數據，將基於此範圍進行分析。")
            
            return hot_tickers

        except Exception as e:
            print(f"❌ 爬蟲遭遇亂流: {e}")
            print("🛡️ 啟動「戰備清單 (Fallback)」模式，載入預設高波動股庫。")
            return self._get_fallback_list(limit)

    def _get_fallback_list(self, limit):
        # 手動維護的「戰備清單」，涵蓋各大飆股板塊
        # 確保在爬蟲失效時，我們還有足夠的樣本 (約 60 檔)
        fallback = [
            # --- 權值/半導體 ---
            "2330.TW", "2454.TW", "2317.TW", "2303.TW", "2308.TW", "2382.TW", "3231.TW", "3443.TW", "3661.TW", "3035.TW",
            # --- AI 伺服器/散熱 ---
            "2376.TW", "2356.TW", "6669.TW", "3017.TW", "3324.TW", "2421.TW", "3037.TW", "2368.TW", "2449.TW", "6271.TW",
            # --- 航運/傳產 ---
            "2603.TW", "2609.TW", "2615.TW", "2618.TW", "2610.TW", "1513.TW", "1519.TW", "1504.TW", "1605.TW", "2002.TW",
            # --- 金融 (波動較小，但為資金避風港) ---
            "2881.TW", "2882.TW", "2891.TW", "2886.TW", "2884.TW",
            # --- 光電/面板/其他熱門 ---
            "2409.TW", "3481.TW", "3008.TW", "2481.TW", "2344.TW", "2408.TW", "6770.TW", "5347.TW", "4961.TW", "9958.TW"
        ]
        return fallback[:limit]

    def download_data_batch(self, tickers):
        print(f"\n📥 開始批次下載 {len(tickers)} 檔股票數據 (這可能需要 30~60 秒)...")
        # 為了提升速度與避免記憶體爆炸，我們只抓最近 '6mo' (半年) 或 '1y' (一年)
        # 動能策略不需要 10 年前的資料
        data = yf.download(tickers, period="1y", group_by='ticker', auto_adjust=True, threads=True) 
        
        # 簡單檢查：有些股票可能下市或改名抓不到，做個清洗
        if data.empty:
            print("❌ 下載失敗，請檢查網路或代號。")
            return None
        
        # 移除下載失敗的空欄位 (Optional)
        data = data.dropna(axis=1, how='all')
        print("✅ 數據下載完成！準備進入篩選階段。")
        return data

# --- 執行單元 ---
manager = StockPoolManagerV2()

# 1. 嘗試抓取 100 檔
hot_list = manager.get_hot_stocks(limit=100)
print(f"目前股票池樣本: {hot_list[:10]} ... (共 {len(hot_list)} 檔)")

# 2. 下載數據
market_data = manager.download_data_batch(hot_list)

# 3. 檢查資料結構
if market_data is not None and not market_data.empty:
    first_stock = hot_list[0]
    if first_stock in market_data.columns.levels[0]:
         print(f"\n📊 預覽龍頭股 [{first_stock}] 數據：")
         print(market_data[first_stock].tail(3))
    else:
         # 處理單一股票回傳格式不同的 edge case
         print(f"\n📊 預覽數據：")
         print(market_data.head(3))
