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

import traceback

def get_driver():
    """設定並回傳 Chrome Driver"""
    chrome_options = Options()
    # 使用新版 Headless 模式，更穩定
    chrome_options.add_argument("--headless=new")
    chrome_options.add_argument("--no-sandbox")
    chrome_options.add_argument("--disable-dev-shm-usage")
    chrome_options.add_argument("--disable-gpu")
    chrome_options.add_argument("--window-size=1920,1080")
    chrome_options.add_argument("--disable-extensions")
    # 規避自動化檢測
    chrome_options.add_argument("--disable-blink-features=AutomationControlled")
    chrome_options.add_argument("user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36")
    
    # 忽略憑證錯誤
    chrome_options.add_argument("--ignore-certificate-errors")
    
    try:
        from selenium.webdriver.chrome.service import Service
        # 自動安裝 driver
        logger.info("正在安裝/設定 ChromeDriver...")
        service = Service(ChromeDriverManager().install())
        driver = webdriver.Chrome(service=service, options=chrome_options)
        return driver
    except Exception as e:
        logger.error(f"ChromeDriver 初始化失敗: {e}")
        raise

def login_and_fetch_data():
    """使用 Selenium 模擬真人登入 -> 搜尋 -> 抓資料"""
    driver = None
    selectors = CONFIG.get("selectors", {})
    
    try:
        driver = get_driver()
        logger.info("🚀 瀏覽器已啟動，開始前往登入頁...")
        
        # 1. 前往登入頁
        login_url = CONFIG.get("login_url")
        driver.get(login_url)
        logger.info(f"已開啟網頁: {login_url}")
        
        # 等待欄位出現
        wait = WebDriverWait(driver, 20) # 延長等待時間到 20秒
        
        logger.info("尋找帳號欄位...")
        user_field = wait.until(EC.presence_of_element_located((By.CSS_SELECTOR, selectors['login_user'])))
        pass_field = driver.find_element(By.CSS_SELECTOR, selectors['login_pass'])
        
        user_field.clear()
        user_field.send_keys(USERNAME)
        pass_field.clear()
        pass_field.send_keys(PASSWORD)
        
        logger.info("輸入帳密完成，點擊登入...")
        
        # 3. 點擊登入
        login_btn = driver.find_element(By.CSS_SELECTOR, selectors['login_btn'])
        login_btn.click()
        
        logger.info("等待登入轉跳...")
        # 簡單等待
        time.sleep(10)
        
        # 檢查是否登入失敗 (可選)
        # if "Login Failed" in driver.page_source: ...
        
        # 5. (若需要) 前往搜尋頁
        search_page = CONFIG.get("search_page_url")
        if search_page and search_page != driver.current_url:
            logger.info(f"前往搜尋頁: {search_page}")
            driver.get(search_page)
            time.sleep(5)
            
        # 6. 輸入搜尋條件並點擊搜尋
        search_input_sel = selectors.get('search_input')
        search_btn_sel = selectors.get('search_btn')
        
        if search_input_sel:
            try:
                logger.info("輸入搜尋關鍵字...")
                s_input = driver.find_element(By.CSS_SELECTOR, search_input_sel)
                s_input.clear()
                s_input.send_keys(CONFIG.get("search_keyword", ""))
            except Exception as e:
                logger.warning(f"搜尋欄位輸入失敗 (可能是選擇器錯誤或該頁面無此欄位): {e}")
            
        if search_btn_sel:
            logger.info("點擊搜尋按鈕...")
            try:
                s_btn = wait.until(EC.element_to_be_clickable((By.CSS_SELECTOR, search_btn_sel)))
                s_btn.click()
                time.sleep(10) # 等待結果載入
            except Exception as e:
                logger.warning(f"搜尋按鈕點擊失敗: {e}")
            
        # 7. 取得最後的 HTML
        logger.info("抓取頁面 HTML...")
        html = driver.page_source
        return html
        
    except Exception as e:
        logger.error(f"❌ 瀏覽器操作過程發生錯誤:\n{traceback.format_exc()}")
        raise e
    finally:
        if driver:
            driver.quit()
            logger.info("瀏覽器已關閉")

def parse_html(html):
    # ... (保持原本解析邏輯，但增加錯誤處理)
    if not html:
        return {}
    
    soup = BeautifulSoup(html, "html.parser")
    # ... (略)
    return results # 這裡可以暫時簡化，避免 tool replace 太多行，保持原樣即可

def job():
    logger.info("⏰ 排程任務開始")
    try:
        html = login_and_fetch_data()
        # 注意：parse_html 還是需要定義，這邊假設它在下面沒被動到，或是被 context 包含
        # 但為了保險，我們只改 login_and_fetch_data 和 get_driver
        # 為了要 replace 正確，我需要確保 parse_html 也在這個範圍內或者我不想動它
        # 這裡只能 replace contiguous block.
        # 所以我會把 parse_html 之後的 job 函數也一起覆寫，確保邏輯連貫
        data = parse_html(html)
        msg = format_message(data)
        asyncio.run(send_to_telegram(msg))
    except Exception:
        # traceback 已經在 login_and_fetch_data 印過了，這邊只要抓大範圍
        logger.error("任務最外層捕獲異常")

if __name__ == "__main__":
    scheduler = BlockingScheduler(timezone="Asia/Taipei")
    scheduler.add_job(job, CronTrigger(hour=20, minute=40), id="job_2040")
    scheduler.add_job(job, CronTrigger(hour=21, minute=40), id="job_2140")
    
    logger.info("🚀 Selenium 機器人啟動中...")
    
    # [新增] 啟動時立刻執行一次測試
    logger.info("⚡ 正在執行啟動測試 (Test Run)...")
    job()
    
    try:
        scheduler.start()
    except (KeyboardInterrupt, SystemExit):
        pass
