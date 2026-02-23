import asyncio
import time
import re
from datetime import datetime
from telethon import TelegramClient
import undetected_chromedriver as uc
from selenium.webdriver.common.by import By
from selenium.webdriver.support.ui import WebDriverWait
from selenium.webdriver.support import expected_conditions as EC
from selenium.common.exceptions import TimeoutException, SessionNotCreatedException, WebDriverException
import os
import json

# ==========================================
# ⚙️ Configuration
# ==========================================
API_ID = int(os.environ.get('API_ID', 33419175))
API_HASH = os.environ.get('API_HASH', '556aa0a8ac62e9cb31ca8b4a9b390d3f')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7965752854:AAEOnQpVt00ZwiHkJFOpheShMOrSkRiWUOw')
TARGET_TELEGRAM_ID = int(os.environ.get('TARGET_TELEGRAM_ID', -1003424776166))
DEVELOPER_NAME = os.environ.get('DEVELOPER_NAME', "RoBoT")

ACCOUNTS_JSON = os.environ.get('ACCOUNTS', '[{"name":"Panel_1","email":"alisasmi.th338@gmail.com","pass":"alisasmi.th338@gmail.com"}]')
ACCOUNTS = json.loads(ACCOUNTS_JSON)

IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

PROCESSED_SIGNATURES = set()

bot = TelegramClient('ivasms_scraper_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ==========================================
# Browser Setup
# ==========================================
def start_browser(panel_name):
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--password-store=basic")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    options.add_argument("--headless=new")
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1280,720")
    options.add_argument("--remote-debugging-port=9222")
    options.add_argument("--disable-blink-features=AutomationControlled")
    options.add_experimental_option("excludeSwitches", ["enable-automation"])
    options.add_experimental_option('useAutomationExtension', False)

    print(f"🚀 {panel_name}: Starting Browser...")
    try:
        driver = uc.Chrome(options=options)
        driver.set_window_size(600, 800)
        return driver
    except Exception as e:
        print(f"\n❌ {panel_name} Error: {e}")
        raise e

# ==========================================
# Login Functions
# ==========================================
def is_login_successful(driver):
    return "portal" in driver.current_url

def is_logged_in(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        return "portal" in driver.current_url
    except:
        return False

def enter_credentials_and_submit(driver, panel_name, email, password):
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
    driver.find_element(By.NAME, "password").send_keys(password)
    login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
    driver.execute_script("arguments[0].click();", login_btn)
    print(f"✅ {panel_name}: Credentials submitted.")

def navigate_to_live_page(driver, panel_name):
    print(f"🌍 {panel_name}: Navigating to Live SMS Page")
    driver.get(IVASMS_LIVE_URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )
    print(f"✅ {panel_name}: Live page loaded successfully.")

def login_ivasms(driver, panel_name, email, password):
    for attempt in range(1, 4):
        print(f"\n🌍 {panel_name}: Login Attempt {attempt}")
        driver.get(IVASMS_LOGIN_URL)
        try:
            wait = WebDriverWait(driver, 20)
            try:
                cloudflare = wait.until(EC.presence_of_element_located(
                    (By.XPATH, "//label[contains(., 'Verify you are human')]/input[@type='checkbox']")
                ))
                cloudflare.click()
                wait.until(EC.presence_of_element_located((By.NAME, "email")))
            except:
                wait.until(EC.presence_of_element_located((By.NAME, "email")))
            
            enter_credentials_and_submit(driver, panel_name, email, password)
            wait.until(is_login_successful)
            print(f"🎉 {panel_name}: Login Successful!")
            return
        except Exception as e:
            if attempt < 3:
                print(f"⚠️ {panel_name}: Retrying...")
                time.sleep(5)
            else:
                raise Exception(f"❌ {panel_name}: Failed to login")

# ==========================================
# Message Processing
# ==========================================
def extract_smart_content(full_msg):
    otp_match = re.search(r'\b(\d{4,8})\b', full_msg)
    if otp_match:
        return otp_match.group(1), "OTP"
    return full_msg, "FULL_DATA"

# ==========================================
# Single Panel Scraping
# ==========================================
async def scrape_single_panel(account_config):
    driver = None
    panel_name = account_config['name']
    email = account_config['email']
    password = account_config['pass']
    chat_id = TARGET_TELEGRAM_ID

    try:
        driver = start_browser(panel_name)
        login_ivasms(driver, panel_name, email, password)
        navigate_to_live_page(driver, panel_name)

        print(f"👀 {panel_name}: Monitoring started...")
        await bot.send_message(chat_id, f"✅ **{panel_name} Started Monitoring**")

        while True:
            try:
                if not is_logged_in(driver):
                    print(f"🚨 {panel_name}: Session expired. Re-login...")
                    await bot.send_message(chat_id, f"**⚠️ Session Expired:** `{panel_name}`")
                    login_ivasms(driver, panel_name, email, password)
                    navigate_to_live_page(driver, panel_name)

                current_time = datetime.now().strftime("%H:%M:%S")
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")

                for row in rows[:5]:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 5:
                            phone = cols[0].text.strip().split('\n')[-1].strip()
                            service = cols[1].text.strip()
                            full_msg = cols[4].text.strip()
                            unique_id = f"{panel_name}_{phone}_{full_msg[:30]}"

                            if unique_id not in PROCESSED_SIGNATURES:
                                content, content_type = extract_smart_content(full_msg)
                                print(f"-> {panel_name}: {service} - {content_type}")

                                if content_type == "OTP":
                                    msg = (f"🗝️ **OTP Received** 🗝️\n"
                                           f"🛡️ **Panel:** `{panel_name}`\n"
                                           f"🛡️ **Service:** `{service}`\n"
                                           f"📱 **Number:** `{phone}`\n"
                                           f"⏳ **Time:** `{current_time}`\n"
                                           f"🔑 **OTP:** `{content}`\n"
                                           f"📝 **Full Message:**\n```\n{full_msg}\n```\n"
                                           f"**Developer:** `{DEVELOPER_NAME}` 👨‍💻")
                                else:
                                    msg = (f"📦 **New SMS** 📦\n"
                                           f"🛡️ **Panel:** `{panel_name}`\n"
                                           f"🛡️ **Service:** `{service}`\n"
                                           f"📱 **Number:** `{phone}`\n"
                                           f"⏳ **Time:** `{current_time}`\n"
                                           f"📝 **Full Message:**\n```\n{full_msg}\n```\n"
                                           f"**Developer:** `{DEVELOPER_NAME}` 👨‍💻")

                                await bot.send_message(chat_id, msg, parse_mode='markdown')
                                PROCESSED_SIGNATURES.add(unique_id)
                    except:
                        continue

            except Exception as e:
                print(f"Error: {e}")
            
            await asyncio.sleep(2)

    except Exception as e:
        error = f"**❌ Failed for {panel_name}:**\n`{e}`"
        print(error)
        await bot.send_message(TARGET_TELEGRAM_ID, error)
    finally:
        if driver:
            try:
                driver.quit()
            except:
                pass

# ==========================================
# Main
# ==========================================
async def main_scraper():
    print(f"Starting {len(ACCOUNTS)} panels...")
    tasks = [scrape_single_panel(account) for account in ACCOUNTS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main_scraper())
