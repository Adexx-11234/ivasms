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
# ⚙️ كوينفجريشن (Configuration)
# ==========================================
# قراءة المتغيرات من البيئة (Railway)
API_ID = int(os.environ.get('API_ID', 33419175))
API_HASH = os.environ.get('API_HASH', '556aa0a8ac62e9cb31ca8b4a9b390d3f')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '7965752854:AAEOnQpVt00ZwiHkJFOpheShMOrSkRiWUOw')
TARGET_TELEGRAM_ID = int(os.environ.get('TARGET_TELEGRAM_ID', -1003424776166))
DEVELOPER_NAME = os.environ.get('DEVELOPER_NAME', "RoBoT")

# قراءة الحسابات من JSON string
ACCOUNTS_JSON = os.environ.get('ACCOUNTS', '[{"name":"Panel_1","email":"alisasmi.th338@gmail.com","pass":"alisasmi.th338@gmail.com"}]')
ACCOUNTS = json.loads(ACCOUNTS_JSON)

# IVASMS Settings
IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

# Duplicate check memory
PROCESSED_SIGNATURES = set()

# Telegram bot start
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
    
    # خيارات مهمة لـ Railway
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
    except SessionNotCreatedException as e:
        print(f"\n❌ {panel_name} ERROR: ChromeDriver version mismatch or browser not found.")
        raise e
    except Exception as e:
        print(f"\n❌ {panel_name} An unexpected error occurred while starting the browser: {e}")
        raise e

# ==========================================
# Login Check Functions
# ==========================================
def is_login_successful(driver):
    return "portal" in driver.current_url

def is_logged_in(driver):
    try:
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        return "portal" in driver.current_url
    except TimeoutException:
        return False
    except Exception:
        return False

# ==========================================
# Login Function
# ==========================================
def enter_credentials_and_submit(driver, panel_name, email, password):
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
    driver.find_element(By.NAME, "password").send_keys(password)
    login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
    driver.execute_script("arguments[0].click();", login_btn)
    print(f"✅ {panel_name}: Credentials submitted.")

def navigate_to_live_page(driver, panel_name):
    print(f"🌍 {panel_name}: Navigating to Live SMS Page: {IVASMS_LIVE_URL}")
    driver.get(IVASMS_LIVE_URL)
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )
    print(f"✅ {panel_name}: Live page loaded successfully.")

def login_ivasms(driver, panel_name, email, password):
    MAX_RETRIES = 3

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🌍 {panel_name}: Going to Login Page (Attempt {attempt}/{MAX_RETRIES}): {IVASMS_LOGIN_URL}")
        driver.get(IVASMS_LOGIN_URL)

        try:
            wait = WebDriverWait(driver, 20)

            # Cloudflare bypass attempt
            try:
                cloudflare_check_box = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//label[contains(., 'Verify you are human')]/input[@type='checkbox']")
                    )
                )
                print(f"✔️ {panel_name}: Cloudflare Checkbox found. Clicking...")
                cloudflare_check_box.click()
                wait.until(EC.presence_of_element_located((By.NAME, "email")))
                print(f"✅ {panel_name}: Cloudflare bypassed/form loaded.")
            except TimeoutException:
                wait.until(EC.presence_of_element_located((By.NAME, "email")))
                print(f"✅ {panel_name}: Cloudflare check skipped/bypassed.")

            # Enter credentials
            enter_credentials_and_submit(driver, panel_name, email, password)

            # Wait for portal URL
            wait.until(is_login_successful)

            print(f"🎉 {panel_name}: Login Successful on attempt {attempt}!")
            return

        except TimeoutException as e:
            if attempt < MAX_RETRIES:
                print(f"⚠️ {panel_name}: Timeout. Login failed or redirect issue. Retrying in 5 seconds...")
                time.sleep(5)
                continue
            else:
                raise TimeoutException(
                    f"❌ {panel_name}: Failed to login after {MAX_RETRIES} attempts. Error: {e}")

        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"⚠️ {panel_name}: Login Failed ({e.__class__.__name__}). Retrying in 5 seconds...")
                time.sleep(5)
                continue
            else:
                raise Exception(
                    f"❌ {panel_name}: Failed to login after {MAX_RETRIES} attempts (Error: {e.__class__.__name__}).")

# ==========================================
# Message Processing
# ==========================================
def extract_smart_content(full_msg):
    otp_match = re.search(r'\b(\d{4,8})\b', full_msg)

    if otp_match:
        return otp_match.group(1), "OTP"
    else:
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

    check_interval = 2
    reload_counter = 0
    reload_threshold = 60

    try:
        driver = start_browser(panel_name)
        login_ivasms(driver, panel_name, email, password)
        navigate_to_live_page(driver, panel_name)

        print(f"👀 {panel_name}: Monitoring started...")
        await bot.send_message(chat_id, f"✅ **{panel_name} Started Monitoring**")

        while True:
            try:
                if not is_logged_in(driver):
                    print(f"\n🚨 {panel_name}: Session expired. Attempting re-login...")
                    await bot.send_message(chat_id, f"**⚠️ Session Expired:** `{panel_name}`. Re-login...")
                    login_ivasms(driver, panel_name, email, password)
                    navigate_to_live_page(driver, panel_name)
                    reload_counter = 0

                reload_counter += 1
                if reload_counter >= reload_threshold:
                    print(f"\n🌐 {panel_name}: Performing periodic page reload...")
                    navigate_to_live_page(driver, panel_name)
                    reload_counter = 0

                current_time = datetime.now().strftime("%H:%M:%S")
                rows = driver.find_elements(By.XPATH, "//table/tbody/tr")

                for row in rows[:5]:
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 5:
                            raw_phone_data = cols[0].text.strip()
                            phone_number = raw_phone_data.split('\n')[-1].strip()
                            service_name = cols[1].text.strip()
                            full_msg = cols[4].text.strip()
                            unique_id = f"{panel_name}_{phone_number}_{full_msg[:30]}"

                            if unique_id not in PROCESSED_SIGNATURES:
                                content_to_send, content_type = extract_smart_content(full_msg)
                                print(f"-> {panel_name} Found {service_name}: {content_type}")

                                msg_template = (
                                    f"{'🗝️ **OTP/CODE Received** 🗝️' if content_type == 'OTP' else '📦 **New SMS Data Received** 📦'}\n"
                                    f"--------------------------------------\n"
                                    f"🛡️ **Panel:** `{panel_name}`\n"
                                    f"🛡️ **Service:** `{service_name}`\n"
                                    f"📱 **Number:** `{phone_number}`\n"
                                    f"⏳ **Time:** `{current_time}`\n"
                                    f"--------------------------------------\n"
                                    f"{f'🔑 **OTP Code:** `   {content_to_send}   `\n' if content_type == 'OTP' else ''}"
                                    f"📝 **Full Message:**\n"
                                    f"```\n{full_msg}\n```\n"
                                    f"**Developer:** `{DEVELOPER_NAME}` 👨‍💻"
                                )
                                await bot.send_message(chat_id, msg_template, parse_mode='markdown')
                                print(f"   -> {panel_name} Sent to Chat ID: {chat_id}")
                                PROCESSED_SIGNATURES.add(unique_id)

                    except Exception as inner_e:
                        print(f"  {panel_name} Inner loop error: {inner_e}")
                        continue

            except TimeoutException as e:
                print(f"\n❌ {panel_name} Timeout during scraping. Retrying navigation...")
                try:
                    navigate_to_live_page(driver, panel_name)
                    reload_counter = 0
                except Exception:
                    print(f"⚠️ {panel_name} Recovery navigation failed.")
            except WebDriverException as e:
                print(f"❌ {panel_name} WebDriver connection issue. Retrying...")
                try:
                    navigate_to_live_page(driver, panel_name)
                    reload_counter = 0
                except Exception:
                    pass
            except Exception as e:
                print(f"Loop Error for {panel_name}: {e.__class__.__name__}")

            await asyncio.sleep(check_interval)

    except Exception as e:
        error_message = f"**❌ CRITICAL Startup Failed for {panel_name}:**\n`{e.__class__.__name__}: {e}`"
        print(f"\n{error_message}")
        await bot.send_message(TARGET_TELEGRAM_ID, error_message)
    finally:
        if driver:
            try:
                await asyncio.sleep(1)
                print(f"🧹 {panel_name}: Closing browser...")
                driver.quit()
            except Exception:
                pass

# ==========================================
# Main Scraper
# ==========================================
async def main_scraper():
    print(f"Starting multi-panel scraper for {len(ACCOUNTS)} accounts...")
    tasks = [scrape_single_panel(account) for account in ACCOUNTS]
    await asyncio.gather(*tasks)
    print("All panel scraping tasks finished.")

if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main_scraper())
