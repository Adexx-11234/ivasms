import os
import re
import json
import time
import random
import asyncio
from datetime import datetime
from telethon import TelegramClient
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC

# ==========================================
# Configuration
# ==========================================
API_ID = int(os.environ.get('API_ID', 33419175))
API_HASH = os.environ.get('API_HASH', '556aa0a8ac62e9cb31ca8b4a9b390d3f')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8731084809:AAHocpvW1ckCo4FdCDTJ5hzaAl156F5eiOQ')
TARGET_TELEGRAM_ID = int(os.environ.get('TARGET_TELEGRAM_ID', -1003857054415))

ACCOUNTS_JSON = os.environ.get('ACCOUNTS', '[{"name":"Panel_1","email":"mohamedsamy3450@gmail.com","pass":"0102068678Soso"}]')
ACCOUNTS = json.loads(ACCOUNTS_JSON)

# Proxy Configuration
PROXY_HOST = "d7cc7bc6400df357.abcproxy.vip"
PROXY_PORT = 4950
PROXY_USER = "Samy1gnQL2801-zone-abc-region-ci"
PROXY_PASS = "q0OQGgu6ec"

IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

PROCESSED_SIGNATURES = set()

# ==========================================
# Telegram Bot Setup
# ==========================================
print("DEBUG: Starting Telegram Client...", flush=True)
bot = TelegramClient('ivasms_scraper_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print("DEBUG: Telegram Client Started.", flush=True)

async def scrape_panel(account):
    panel_name = account['name']
    email = account['email']
    password = account['pass']
    
    while True:
        driver = None
        try:
            print(f"🚀 {panel_name}: Starting Light-weight Selenium...", flush=True)
            
            options = uc.ChromeOptions()
            options.add_argument("--no-sandbox")
            options.add_argument("--disable-dev-shm-usage")
            options.add_argument("--disable-gpu")
            options.add_argument("--window-size=1280,720")
            
            # إعدادات لتقليل استهلاك الرام
            options.add_argument("--disable-extensions")
            options.add_argument("--proxy-server=http://%s:%s@%s:%s" % (PROXY_USER, PROXY_PASS, PROXY_HOST, PROXY_PORT))
            
            # منع تحميل الصور لتوفير الرام والسرعة
            prefs = {"profile.managed_default_content_settings.images": 2}
            options.add_experimental_option("prefs", prefs)
            
            # تشغيل المتصفح في وضع headless
            driver = uc.Chrome(options=options, headless=True)
            
            print(f"🌍 {panel_name}: Navigating to login page...", flush=True)
            driver.get(IVASMS_LOGIN_URL)
            
            # انتظار أطول قليلاً بسبب بطء الرام
            time.sleep(random.randint(30, 45))
            
            wait = WebDriverWait(driver, 90) # زيادة وقت الانتظار لـ 90 ثانية
            
            print(f"🔍 {panel_name}: Searching for login fields...", flush=True)
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            
            print(f"📝 {panel_name}: Entering credentials...", flush=True)
            email_field.send_keys(email)
            time.sleep(1)
            
            pass_field = driver.find_element(By.NAME, "password")
            pass_field.send_keys(password)
            time.sleep(1)
            
            login_btn = driver.find_element(By.CSS_SELECTOR, 'button[type="submit"]')
            login_btn.click()
            
            print(f"DEBUG: {panel_name} Waiting for redirect...", flush=True)
            time.sleep(25)
            
            if "portal" not in driver.current_url:
                print(f"⚠️ {panel_name}: Login failed, current URL: {driver.current_url}", flush=True)
                time.sleep(15)
                if "portal" not in driver.current_url:
                    raise Exception("Login failed - Check credentials or Cloudflare")

            print(f"✅ {panel_name}: Login successful", flush=True)
            await bot.send_message(TARGET_TELEGRAM_ID, f"✅ **{panel_name} started monitoring (Light Mode)**")
            
            driver.get(IVASMS_LIVE_URL)
            time.sleep(15)

            while True:
                try:
                    driver.refresh()
                    time.sleep(20)
                    
                    rows = driver.find_elements(By.CSS_SELECTOR, 'table tbody tr')
                    
                    if not rows:
                        print(f"ℹ️ {panel_name}: No messages found.", flush=True)
                        continue

                    for row in rows[:10]:
                        try:
                            cols = row.find_elements(By.TAG_NAME, 'td')
                            if len(cols) >= 5:
                                phone = cols[0].text.strip()
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
                        except: continue
                    
                    if len(PROCESSED_SIGNATURES) > 1000: PROCESSED_SIGNATURES.clear()
                    time.sleep(40)
                except Exception as e:
                    print(f"⚠️ {panel_name} Loop Error: {e}", flush=True)
                    break 
        except Exception as e:
            print(f"❌ {panel_name} CRASHED: {e}", flush=True)
        finally:
            if driver:
                try: driver.quit()
                except: pass
            print(f"🔄 {panel_name}: Restarting in 60 seconds...", flush=True)
            await asyncio.sleep(60)

async def main():
    tasks = [scrape_panel(acc) for acc in ACCOUNTS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main())
