import os
import logging
import yaml
import time
import asyncio
from datetime import datetime
from bs4 import BeautifulSoup
from telegram import Bot
from telegram.error import TelegramError
from apscheduler.schedulers.blocking import BlockingScheduler
from apscheduler.triggers.cron import CronTrigger

from selenium import webdriver
from selenium.webdriver.chrome.options import Options
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from webdriver_manager.chrome import ChromeDriverManager

# 設定日誌
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)
logger = logging.getLogger(__name__)

# 讀取 Config
def load_config():
    with open("config.yaml", "r", encoding="utf-8") as f:
        return yaml.safe_load(f)

CONFIG = load_config()

# 環境變數
BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("CHAT_ID")
USERNAME = os.getenv("TARGET_USERNAME")
PASSWORD = os.getenv("TARGET_PASSWORD")

bot = Bot(token=BOT_TOKEN)

def get_driver():
    """設定並回傳 Chrome Driver"""
    chrome_options = Options()
    chrome_options.add_argument("--headless") # 無頭模式 (不顯示視窗)
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/90.0.4430.212 Safari/537.36")
    
    # 自動安裝對應版本的可執行檔
    from selenium.webdriver.chrome.service import Service
    # 注意：在 Docker 內通常不需要 ChromeDriverManager().install() 下載，直接用系統的 chromedriver
    # 但為了相容性，我們先嘗試用 WebDriverManager
    try:
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
    except:
        # 備援：直接呼叫系統路徑 (Docker 環境常見)
        driver = webdriver.Chrome(options=chrome_options)
        
    return driver

def login_and_fetch_data():
    """使用 Selenium 模擬真人登入 -> 搜尋 -> 抓資料"""
    driver = get_driver()
    selectors = CONFIG.get("selectors", {})
    
    try:
        logger.info("🚀 啟動瀏覽器...")
        
        # 1. 前往登入頁
        login_url = CONFIG.get("login_url")
        driver.get(login_url)
        logger.info(f"前往登入頁: {login_url}")
        
        # 等待欄位出現
        wait = WebDriverWait(driver, 10)
        
        # 2. 輸入帳密
        user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors['login_user'])))
        pass_field = driver.find_element(By.CSS_SELECTOR, selectors['login_pass'])
        
        user_field.clear()
        user_field.send_keys(USERNAME)
        pass_field.clear()
        pass_field.send_keys(PASSWORD)
        
        logger.info("輸入帳密完成")
        
        # 3. 點擊登入
        login_btn = driver.find_element(By.CSS_SELECTOR, selectors['login_btn'])
        login_btn.click()
        logger.info("點擊登入按鈕")
        
        # 4. 等待登入後跳轉或確保登入成功
        # (這裡簡單等待幾秒，或您可以加 wait.until(EC.url_contains(...))
        time.sleep(5) 
        
        # 5. (若需要) 前往搜尋頁
        search_page = CONFIG.get("search_page_url")
        if search_page and search_page != driver.current_url:
            driver.get(search_page)
            time.sleep(3)
            
        # 6. 輸入搜尋條件並點擊搜尋
        search_input_sel = selectors.get('search_input')
        search_btn_sel = selectors.get('search_btn')
        
        if search_input_sel:
            s_input = driver.find_element(By.CSS_SELECTOR, search_input_sel)
            s_input.clear()
            s_input.send_keys(CONFIG.get("search_keyword", ""))
            
        if search_btn_sel:
            s_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, search_btn_sel)))
            s_btn.click()
            logger.info("點擊搜尋按鈕")
            time.sleep(5) # 等待結果載入
            
        # 7. 取得最後的 HTML
        html = driver.page_source
        return html
        
    except Exception as e:
        logger.error(f"瀏覽器操作失敗: {e}")
        # 截圖方便除錯
        driver.save_screenshot("error_screenshot.png")
        raise
    finally:
        driver.quit()
        logger.info("瀏覽器已關閉")

def parse_html(html):
    soup = BeautifulSoup(html, "html.parser")
    results = {}
    fields = CONFIG.get("fields", [])
    
    for field in fields:
        name = field["name"]
        selector = field["selector"]
        elem = soup.select_one(selector)
        results[name] = elem.get_text(strip=True) if elem else "N/A"
        
    return results

def format_message(data):
    msg_lines = [f"📅 *自動抓取報告* ({datetime.now().strftime('%H:%M')})"]
    msg_lines.append("")
    for k, v in data.items():
        msg_lines.append(f"*{k}*: `{v}`")
    return "\n".join(msg_lines)

async def send_to_telegram(message):
    try:
        await bot.send_message(chat_id=CHAT_ID, text=message, parse_mode="Markdown")
        logger.info("✅ 訊息已發送至 Telegram")
    except TelegramError as e:
        logger.error(f"❌ 發送失敗: {e}")

def job():
    logger.info("⏰ 排程任務開始")
    try:
        html = login_and_fetch_data()
        data = parse_html(html)
        msg = format_message(data)
        asyncio.run(send_to_telegram(msg))
    except Exception as e:
        logger.error(f"❌ 任務失敗: {e}")

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(job, CronTrigger(hour=20, minute=40), id="job_2040")
    scheduler.add_job(job, CronTrigger(hour=21, minute=40), id="job_2140")
    
    logger.info("🚀 Selenium 機器人啟動中...")
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
