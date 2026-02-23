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

# ==========================================
# ⚙️ কনফিগারেশন (Configuration)
# ==========================================
# টেলিগ্রাম সেটিংস
API_ID = 33419175
API_HASH = '556aa0a8ac62e9cb31ca8b4a9b390d3f'
BOT_TOKEN = '7965752854:AAEOnQpVt00ZwiHkJFOpheShMOrSkRiWUOw'

# ✅ টেলিগ্রাম মেসেজ পাঠানোর টার্গেট ID (সব মেসেজ এখানে যাবে)
TARGET_TELEGRAM_ID = -1003424776166

# 👤 ডেভেলপার নাম (Developer Name)
DEVELOPER_NAME = "RoBoT"  # <-- এটা পরিবর্তন করুন!

# IVASMS সেটিংস
IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

# 🔑 একাধিক IVASMS প্যানেলের ক্রেডেনশিয়াল
ACCOUNTS = [

    {
        "name": "Panel_1",
        "email": "alisasmi.th338@gmail.com",
        "pass": "alisasmi.th338@gmail.com",
    }

]

# ডুপ্লিকেট চেক করার মেমোরি
PROCESSED_SIGNATURES = set()

# টেলিগ্রাম বট স্টার্ট
bot = TelegramClient('ivasms_scraper_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)


# ==========================================
# 🛡️ ব্রাউজার সেটআপ
# ==========================================
def start_browser(panel_name):
    options = uc.ChromeOptions()
    options.add_argument("--no-first-run")
    options.add_argument("--password-store=basic")
    options.add_argument("--disable-popup-blocking")
    options.add_argument("--disable-infobars")
    # options.add_argument("--headless")

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
# 🎯 কাস্টম এক্সপেক্টেশন এবং চেক
# ==========================================
def is_login_successful(driver):
    """
    Portal URL-এ পৌঁছানো হয়েছে কিনা তা যাচাই করে।
    """
    return "portal" in driver.current_url


def is_logged_in(driver):
    """
    Checks if the user is currently logged into the IVASMS portal
    by checking for the presence of the main content table.
    """
    try:
        # Check for the presence of the table, which confirms active session
        WebDriverWait(driver, 5).until(
            EC.presence_of_element_located((By.TAG_NAME, "table"))
        )
        # Also check if the current URL has been redirected back to the login page.
        return "portal" in driver.current_url
    except TimeoutException:
        return False
    except Exception:
        return False


# ==========================================
# 📝 ক্রেডেনশিয়াল প্রবেশ এবং সাবমিট
# ==========================================
def enter_credentials_and_submit(driver, panel_name, email, password):
    """
    লগইন ফর্মে ইমেইল, পাসওয়ার্ড প্রবেশ করায় এবং সাবমিট করে।
    """
    wait = WebDriverWait(driver, 10)
    wait.until(EC.presence_of_element_located((By.NAME, "email"))).send_keys(email)
    driver.find_element(By.NAME, "password").send_keys(password)
    login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
    driver.execute_script("arguments[0].click();", login_btn)
    print(f"✅ {panel_name}: Credentials submitted.")


# ==========================================
# 🔄 সাহায্যকারী ফাংশন: লাইভ পেজে যাওয়া
# ==========================================
def navigate_to_live_page(driver, panel_name):
    """
    Attempts to navigate to the live SMS URL and waits for the table.
    Raises TimeoutException if the table is not found.
    """
    print(f"🌍 {panel_name}: Navigating to Live SMS Page: {IVASMS_LIVE_URL}")
    driver.get(IVASMS_LIVE_URL)

    # Wait for the main content table, which confirms the page is loaded and logged in
    WebDriverWait(driver, 10).until(
        EC.presence_of_element_located((By.TAG_NAME, "table"))
    )
    print(f"✅ {panel_name}: Live page loaded successfully.")


# ==========================================
# 📥 লগইন ফাংশন (৩ বার চেষ্টা করবে)
# ==========================================
def login_ivasms(driver, panel_name, email, password):
    MAX_RETRIES = 3

    for attempt in range(1, MAX_RETRIES + 1):
        print(f"\n🌍 {panel_name}: Going to Login Page (Attempt {attempt}/{MAX_RETRIES}): {IVASMS_LOGIN_URL}")
        driver.get(IVASMS_LOGIN_URL)

        try:
            wait = WebDriverWait(driver, 20)

            # 1. Cloudflare CAPTCHA বাইপাস/ক্লিক করার চেষ্টা
            try:
                cloudflare_check_box = wait.until(
                    EC.presence_of_element_located(
                        (By.XPATH, "//label[contains(., 'Verify you are human')]/input[@type='checkbox']"))
                )
                print(f"✔️ {panel_name}: Cloudflare Checkbox found. Clicking...")
                cloudflare_check_box.click()
                wait.until(EC.presence_of_element_located((By.NAME, "email")))
                print(f"✅ {panel_name}: Cloudflare bypassed/form loaded.")

            except TimeoutException:
                wait.until(EC.presence_of_element_located((By.NAME, "email")))
                print(f"✅ {panel_name}: Cloudflare check skipped/bypassed.")

            # 2. ক্রেডেনশিয়াল প্রবেশ এবং সাবমিট
            enter_credentials_and_submit(driver, panel_name, email, password)

            # 3. পোর্টাল URL এ সফলভাবে পৌঁছানোর জন্য অপেক্ষা
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
                    f"❌ {panel_name}: Failed to login after {MAX_RETRIES} attempts (Timeout/Unresolved Cloudflare/Credentials Issue). Error: {e}")

        except Exception as e:
            if attempt < MAX_RETRIES:
                print(f"⚠️ {panel_name}: Login Failed ({e.__class__.__name__}). Retrying in 5 seconds...")
                time.sleep(5)
                continue
            else:
                raise Exception(
                    f"❌ {panel_name}: Failed to login after {MAX_RETRIES} attempts (Error: {e.__class__.__name__}).")


# ==========================================
# 🔍 স্মার্ট মেসেজ প্রসেসিং লজিক
# ==========================================
def extract_smart_content(full_msg):
    """
    মেসেজ থেকে OTP (4-8 ডিজিট) বা পুরো টেক্সট রিটার্ন করবে।
    """
    otp_match = re.search(r'\b(\d{4,8})\b', full_msg)

    if otp_match:
        return otp_match.group(1), "OTP"
    else:
        return full_msg, "FULL_DATA"


# ==========================================
# 📥 সিঙ্গেল প্যানেল স্ক্র্যাপিং লজিক (Updated for Resilience)
# ==========================================
async def scrape_single_panel(account_config):
    driver = None
    panel_name = account_config['name']
    email = account_config['email']
    password = account_config['pass']
    chat_id = TARGET_TELEGRAM_ID

    # Session Management Variables
    check_interval = 2  # 2 seconds between checks
    reload_counter = 0
    reload_threshold = 60  # Reload every 120 seconds (2 minutes)

    try:
        driver = start_browser(panel_name)

        # Initial Login
        login_ivasms(driver, panel_name, email, password)
        # Navigate to the live page after initial login
        navigate_to_live_page(driver, panel_name)

        print(f"👀 {panel_name}: Monitoring started...")

        while True:
            try:
                # 1. Session Check and Re-login Logic
                if not is_logged_in(driver):
                    print(f"\n🚨 {panel_name}: Session expired/logged out detected. Attempting re-login...")
                    await bot.send_message(chat_id, f"**⚠️ Session Expired:** `{panel_name}`. Attempting re-login...")
                    login_ivasms(driver, panel_name, email, password)
                    navigate_to_live_page(driver, panel_name)  # Navigate to live page after re-login
                    reload_counter = 0  # Reset counter after successful re-login

                # 2. Periodic Reload Logic
                reload_counter += 1
                if reload_counter >= reload_threshold:
                    print(f"\n🌐 {panel_name}: Performing periodic page reload to maintain session...")
                    navigate_to_live_page(driver, panel_name)  # Use the robust navigation function
                    reload_counter = 0  # Reset counter

                # 3. Scraping Logic
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

                                # Message Formatting (OTP / FULL_DATA)
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
                                # টেলিগ্রামে সেন্ড
                                await bot.send_message(chat_id, msg_template, parse_mode='markdown')
                                print(f"   -> {panel_name} Sent to Chat ID: {chat_id}")
                                PROCESSED_SIGNATURES.add(unique_id)

                    except Exception as inner_e:
                        print(f"  {panel_name} Inner loop error (skipping row): {inner_e}")
                        continue

            except TimeoutException as e:
                # Handle the Timeout error during scraping/reload. Try to recover.
                print(f"\n❌ {panel_name} Timeout during scraping/reload. Retrying navigation...")
                try:
                    # Attempt to re-navigate to the live page to clear the state
                    navigate_to_live_page(driver, panel_name)
                    reload_counter = 0  # Reset counter after successful recovery
                except Exception:
                    # If re-navigation fails, the session might be truly lost. The next iteration will trigger re-login.
                    print(f"⚠️ {panel_name} Recovery navigation failed. Checking login status next iteration.")

            except WebDriverException as e:
                # If connection is lost or another serious WebDriver error occurs, still try to recover.
                print(f"❌ {panel_name} WebDriver connection issue detected. Retrying navigation...")
                try:
                    navigate_to_live_page(driver, panel_name)
                    reload_counter = 0
                except Exception:
                    print(
                        f"⚠️ {panel_name} Critical WebDriver error. The browser may be unstable. Checking login status next iteration.")

            except Exception as e:
                print(f"Loop Error for {panel_name}: {e.__class__.__name__}. Continuing loop.")

            await asyncio.sleep(check_interval)

    except Exception as e:
        # Catch errors during start_browser or initial login (fatal errors)
        error_message = f"**❌ CRITICAL Startup Failed for {panel_name}:**\n`{e.__class__.__name__}: {e}`"
        print(f"\n{error_message}")
        await bot.send_message(TARGET_TELEGRAM_ID, error_message)

    finally:
        if driver:
            try:
                await asyncio.sleep(1)
                print(f"🧹 {panel_name}: Closing browser...")
                driver.quit()
                print(f"{panel_name}: Browser closed successfully.")
            except Exception as quit_e:
                # Ignoring the OSError: [WinError 6] here as it's a known uc bug.
                print(f"⚠️ {panel_name} Browser quit attempt finished (OSError ignored).")
                pass


# ==========================================
# 🚀 মেইন মাল্টি-স্ক্র্যাপিং লজিক
# ==========================================
async def main_scraper():
    print(f"Starting multi-panel scraper for {len(ACCOUNTS)} accounts...")

    tasks = [scrape_single_panel(account) for account in ACCOUNTS]

    await asyncio.gather(*tasks)

    print("All panel scraping tasks finished.")


if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main_scraper())
