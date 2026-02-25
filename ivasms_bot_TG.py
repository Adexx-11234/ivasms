import asyncio
import time
import re
from datetime import datetime
from telethon import TelegramClient
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, WebDriverException
import os
import json
import sys

# ==========================================
# Configuration
# ==========================================
API_ID = int(os.environ.get('API_ID', 33419175))
API_HASH = os.environ.get('API_HASH', '556aa0a8ac62e9cb31ca8b4a9b390d3f')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8731084809:AAHocpvW1ckCo4FdCDTJ5hzaAl156F5eiOQ')
TARGET_TELEGRAM_ID = int(os.environ.get('TARGET_TELEGRAM_ID', -1003857054415))

ACCOUNTS_JSON = os.environ.get('ACCOUNTS', '[{"name":"Panel_1","email":"mohamedsamy3450@gmail.com","pass":"0102068678Soso"}]')
ACCOUNTS = json.loads(ACCOUNTS_JSON)

IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

PROCESSED_SIGNATURES = set()

# إعداد البوت مع طباعة للتأكد من الاتصال
print("DEBUG: Starting Telegram Client...", flush=True)
bot = TelegramClient('ivasms_scraper_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print("DEBUG: Telegram Client Started.", flush=True)

# ==========================================
# Browser Setup
# ==========================================
def start_browser(panel_name):
    print(f"DEBUG: Entering start_browser for {panel_name}", flush=True)
    options = uc.ChromeOptions()
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--disable-extensions")
    options.add_argument("--window-size=1280,720")
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36')
    
    print(f"🚀 {panel_name}: Initializing uc.Chrome...", flush=True)
    try:
        driver = uc.Chrome(options=options, use_subprocess=True)
        driver.set_page_load_timeout(90)
        print(f"DEBUG: {panel_name} Browser initialized successfully", flush=True)
        return driver
    except Exception as e:
        print(f"❌ {panel_name} Browser Error: {e}", flush=True)
        raise e

# ==========================================
# Login Functions
# ==========================================
def login_ivasms(driver, panel_name, email, password):
    print(f"🌍 {panel_name}: Navigating to login page...", flush=True)
    
    for attempt in range(1, 4):
        try:
            driver.get(IVASMS_LOGIN_URL)
            print(f"DEBUG: {panel_name} Page loaded, waiting for elements...", flush=True)
            time.sleep(10)
            
            wait = WebDriverWait(driver, 40)
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))

            print(f"📝 {panel_name}: Entering credentials (Attempt {attempt})...", flush=True)
            email_field.clear()
            email_field.send_keys(email)
            
            pass_field = driver.find_element(By.NAME, "password")
            pass_field.clear()
            pass_field.send_keys(password)
            
            login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            driver.execute_script("arguments[0].click();", login_btn)
            
            print(f"DEBUG: {panel_name} Login button clicked, waiting for redirect...", flush=True)
            time.sleep(15)
            
            if "portal" in driver.current_url:
                print(f"✅ {panel_name}: Login successful", flush=True)
                return True
            else:
                print(f"⚠️ {panel_name}: Login failed, current URL: {driver.current_url}", flush=True)
                
        except Exception as e:
            print(f"⚠️ {panel_name}: Attempt {attempt} error - {e}", flush=True)
        
        time.sleep(10)
    
    return False

def navigate_to_live_page(driver, panel_name):
    print(f"🌍 {panel_name}: Navigating to live page...", flush=True)
    try:
        driver.get(IVASMS_LIVE_URL)
        wait = WebDriverWait(driver, 40)
        wait.until(EC.presence_of_element_located((By.TAG_NAME, "table")))
        print(f"DEBUG: {panel_name} Live page table found.", flush=True)
        return True
    except Exception as e:
        print(f"❌ {panel_name}: Navigation error - {e}", flush=True)
        return False

# ==========================================
# Scraping Function
# ==========================================
async def scrape_panel(account):
    panel_name = account['name']
    email = account['email']
    password = account['pass']
    driver = None
    
    while True:
        try:
            if not driver:
                driver = start_browser(panel_name)
            
            if not login_ivasms(driver, panel_name, email, password):
                raise Exception("Login failed after multiple attempts")
            
            if not navigate_to_live_page(driver, panel_name):
                raise Exception("Could not reach live page")
            
            await bot.send_message(TARGET_TELEGRAM_ID, f"✅ **{panel_name} started monitoring**")
            print(f"DEBUG: {panel_name} Monitoring started message sent to Telegram.", flush=True)
            
            while True:
                try:
                    driver.refresh()
                    time.sleep(7)
                    
                    wait = WebDriverWait(driver, 30)
                    rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table/tbody/tr")))
                    
                    for row in rows[:10]:
                        try:
                            cols = row.find_elements(By.TAG_NAME, "td")
                            if len(cols) >= 5:
                                phone_text = cols[0].text.strip()
                                phone = phone_text.split('\n')[-1] if '\n' in phone_text else phone_text
                                service = cols[1].text.strip()
                                message = cols[4].text.strip()
                                
                                msg_id = f"{panel_name}_{phone}_{message[:50]}"
                                
                                if msg_id not in PROCESSED_SIGNATURES:
                                    otp_match = re.search(r'\b(\d{4,8})\b', message)
                                    otp = otp_match.group(1) if otp_match else None
                                    time_now = datetime.now().strftime("%H:%M:%S")
                                    
                                    if otp:
                                        msg = (f"🔑 **OTP Received**\n"
                                               f"📱 **Number:** `{phone}`\n"
                                               f"🛡️ **Service:** `{service}`\n"
                                               f"🔢 **Code:** `{otp}`\n"
                                               f"⏱️ **Time:** `{time_now}`\n"
                                               f"📝 **Full:**\n```\n{message}\n```")
                                    else:
                                        msg = (f"📨 **New SMS**\n"
                                               f"📱 **Number:** `{phone}`\n"
                                               f"🛡️ **Service:** `{service}`\n"
                                               f"⏱️ **Time:** `{time_now}`\n"
                                               f"📝 **Message:**\n```\n{message}\n```")
                                    
                                    await bot.send_message(TARGET_TELEGRAM_ID, msg)
                                    PROCESSED_SIGNATURES.add(msg_id)
                                    print(f"✅ {panel_name}: Sent message from {phone}", flush=True)
                                    
                        except Exception:
                            continue
                    
                    if len(PROCESSED_SIGNATURES) > 1000:
                        PROCESSED_SIGNATURES.clear()
                        
                    await asyncio.sleep(15)
                    
                except Exception as e:
                    print(f"⚠️ {panel_name} Loop Error: {e}", flush=True)
                    if "session" in str(e).lower() or "disconnected" in str(e).lower():
                        break
                    await asyncio.sleep(15)
                    
        except Exception as e:
            error_msg = f"❌ **{panel_name} CRASHED**\n`{str(e)}`"
            print(error_msg, flush=True)
            try:
                await bot.send_message(TARGET_TELEGRAM_ID, error_msg)
            except:
                pass
        finally:
            if driver:
                try:
                    driver.quit()
                except:
                    pass
                driver = None
            print(f"🔄 {panel_name}: Restarting in 30 seconds...", flush=True)
            await asyncio.sleep(30)

async def main():
    print(f"DEBUG: Starting main with {len(ACCOUNTS)} accounts", flush=True)
    tasks = [scrape_panel(acc) for acc in ACCOUNTS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main())
