# Telegram 自動抓取機器人 (Selenium 版)

這是一個自動化爬蟲工具，使用 **Selenium** 模擬真人開啟 Chrome 瀏覽器，解決複雜的登入驗證問題。
它會每天定時 (20:40, 21:40) 執行抓取任務。

## 📁 檔案結構
- `crawler_bot.py`: 主程式 (包含 Selenium 邏輯)。
- `config.yaml`: 設定檔 (定義選取器 Selectors)。
- `Dockerfile`: 雲端部署設定 (包含安裝 Chrome)。
- `requirements.txt`: 套件清單。

## 🚀 快速開始

### 1. 準備環境變數
在部署平台 (如 Zeabur) 上設定以下變數：
- `BOT_TOKEN`: Telegram Bot Token
- `CHAT_ID`: 您的 Chat ID
- `TARGET_USERNAME`: 目標網站帳號
- `TARGET_PASSWORD`: 目標網站密碼

### 2. 修改設定檔 (`config.yaml`)
這是最關鍵的一步！請打開目標網站，按 F12 觀察，並填入正確的 **CSS Selectors**：
```yaml
selectors:
  login_user: "input[name='username']"  # 帳號欄位
  login_pass: "input[name='password']"  # 密碼欄位
  login_btn:  "button[type='submit']"   # 登入按鈕
  search_btn: "button.search-btn"       # 搜尋按鈕
```

### 3. 部署到雲端 (Zeabur)
1. 把專案推送到 GitHub。
2. 在 Zeabur 建立專案 -> 連接 GitHub。
3. Zeabur 會自動讀取 `Dockerfile` 並開始安裝 (包含 Chrome)。
4. 部署完成後，記得去設定上述的環境變數。

## 🛠 本地測試
若要在自己電腦上跑，請確保有安裝 Chrome 瀏覽器。
```bash
pip install -r requirements.txt
# 設定環境變數後執行
python crawler_bot.py
```

## ❓ 常見問題
**Q: 為什麼抓不到資料？**
A: 可能是網頁載入太慢。可以試著將程式碼裡的 `time.sleep(5)`秒數加大，或檢查 Selector 是否有變。
