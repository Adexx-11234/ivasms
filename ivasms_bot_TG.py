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

# ==========================================
# Configuration
# ==========================================
API_ID = int(os.environ.get('API_ID', 33419175))
API_HASH = os.environ.get('API_HASH', '556aa0a8ac62e9cb31ca8b4a9b390d3f')
BOT_TOKEN = os.environ.get('BOT_TOKEN', '8731084809:AAHocpvW1ckCo4FdCDTJ5hzaAl156F5eiOQ')
TARGET_TELEGRAM_ID = int(os.environ.get('TARGET_TELEGRAM_ID', -1003857054415))
DEVELOPER_NAME = os.environ.get('DEVELOPER_NAME', "X~DeV")

ACCOUNTS_JSON = os.environ.get('ACCOUNTS', '[{"name":"Panel_1","email":"mohamedsamy3450@gmail.com","pass":"0102068678Soso"}]')
ACCOUNTS = json.loads(ACCOUNTS_JSON)

IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

PROCESSED_SIGNATURES = set()

bot = TelegramClient('ivasms_scraper_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)

# ==========================================
# Browser Setup - النسخة المصححة للعمل على Railway
# ==========================================
def start_browser(panel_name):
    options = uc.ChromeOptions()
    
    # إعدادات ضرورية للتشغيل في بيئة Docker/Railway
    options.add_argument("--headless=new") # تشغيل بدون واجهة رسومية
    options.add_argument("--no-sandbox")
    options.add_argument("--disable-dev-shm-usage")
    options.add_argument("--disable-gpu")
    options.add_argument("--window-size=1920,1080")
    
    # إضافة User-Agent لتقليل احتمالية الكشف
    options.add_argument('--user-agent=Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36')

    print(f"🚀 {panel_name}: Starting Browser...")
    try:
        # ملاحظة: تم حذف version_main=114 ليقوم السكريبت بتحميل الإصدار المتوافق تلقائياً
        driver = uc.Chrome(options=options, use_subprocess=True) 
        return driver
    except Exception as e:
        print(f"❌ {panel_name} Browser Error: {e}")
        raise e

# ==========================================
# Login Functions
# ==========================================
def is_login_successful(driver):
    try:
        return "portal" in driver.current_url
    except:
        return False

def login_ivasms(driver, panel_name, email, password):
    print(f"🌍 {panel_name}: Logging in...")
    
    for attempt in range(1, 4):
        try:
            driver.get(IVASMS_LOGIN_URL)
            time.sleep(5) # زيادة وقت الانتظار للتحميل
            
            # انتظار ظهور حقل الإيميل للتأكد من تحميل الصفحة
            wait = WebDriverWait(driver, 20)
            email_field = wait.until(EC.presence_of_element_located((By.NAME, "email")))
            
            # إدخال الإيميل
            email_field.clear()
            email_field.send_keys(email)
            
            # إدخال الباسورد
            pass_field = driver.find_element(By.NAME, "password")
            pass_field.clear()
            pass_field.send_keys(password)
            
            # الضغط على زر الدخول
            login_btn = driver.find_element(By.XPATH, "//button[@type='submit']")
            driver.execute_script("arguments[0].click();", login_btn)
            
            time.sleep(7)
            
            if "portal" in driver.current_url:
                print(f"✅ {panel_name}: Login successful")
                return True
            else:
                print(f"⚠️ {panel_name}: Attempt {attempt} failed - Current URL: {driver.current_url}")
                # محاولة أخذ لقطة شاشة للديبرج (اختياري)
                # driver.save_screenshot(f"login_failed_{panel_name}_{attempt}.png")
                
        except Exception as e:
            print(f"⚠️ {panel_name}: Attempt {attempt} error - {e}")
        
        time.sleep(5)
    
    print(f"❌ {panel_name}: Login failed after 3 attempts")
    return False

def navigate_to_live_page(driver, panel_name):
    print(f"🌍 {panel_name}: Going to live page...")
    try:
        driver.get(IVASMS_LIVE_URL)
        time.sleep(7)
        return True
    except Exception as e:
        print(f"❌ {panel_name}: Navigation error - {e}")
        return False

# ==========================================
# Message Processing
# ==========================================
def extract_otp(text):
    # تحسين استخراج الكود ليشمل أنماط أكثر
    match = re.search(r'\b(\d{4,8})\b', text)
    return match.group(1) if match else None

# ==========================================
# Scraping Function
# ==========================================
async def scrape_panel(account):
    panel_name = account['name']
    email = account['email']
    password = account['pass']
    driver = None
    
    try:
        driver = start_browser(panel_name)
        
        if not login_ivasms(driver, panel_name, email, password):
            raise Exception("Login failed - Check credentials or site accessibility")
        
        if not navigate_to_live_page(driver, panel_name):
            raise Exception("Navigation to live page failed")
        
        # إرسال رسالة بدء التشغيل
        try:
            await bot.send_message(TARGET_TELEGRAM_ID, f"✅ **{panel_name} started monitoring**")
        except Exception as e:
            print(f"⚠️ Telegram error: {e}")
        
        while True:
            try:
                # تحديث الصفحة كل دورة
                driver.refresh()
                time.sleep(5)
                
                # انتظار ظهور الجدول
                wait = WebDriverWait(driver, 15)
                rows = wait.until(EC.presence_of_all_elements_located((By.XPATH, "//table/tbody/tr")))
                
                for row in rows[:10]:  # آخر 10 رسائل
                    try:
                        cols = row.find_elements(By.TAG_NAME, "td")
                        if len(cols) >= 5:
                            # استخراج رقم الهاتف
                            phone_text = cols[0].text.strip()
                            phone = phone_text.split('\n')[-1] if '\n' in phone_text else phone_text
                            
                            service = cols[1].text.strip()
                            message = cols[4].text.strip()
                            
                            # تجنب التكرار باستخدام الهاتف والرسالة
                            msg_id = f"{panel_name}_{phone}_{message[:50]}"
                            
                            if msg_id not in PROCESSED_SIGNATURES:
                                otp = extract_otp(message)
                                time_now = datetime.now().strftime("%H:%M:%S")
                                
                                # تنسيق الرسالة
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
                                
                                # محاولة إرسال الرسالة
                                try:
                                    await bot.send_message(TARGET_TELEGRAM_ID, msg)
                                    PROCESSED_SIGNATURES.add(msg_id)
                                    print(f"✅ {panel_name}: Sent new message from {phone}")
                                except Exception as e:
                                    print(f"⚠️ {panel_name}: Failed to send to Telegram - {e}")
                                
                                await asyncio.sleep(1)  # تجنب السبام
                                
                    except Exception as e:
                        continue
                
                # تنظيف الـ signatures القديمة لتوفير الذاكرة (اختياري)
                if len(PROCESSED_SIGNATURES) > 1000:
                    PROCESSED_SIGNATURES.clear()

                await asyncio.sleep(10)  # انتظار 10 ثواني بين الدورات لتقليل الضغط
                
            except Exception as e:
                print(f"⚠️ {panel_name}: Loop error - {e}")
                # إذا حدث خطأ في المتصفح، نحاول إعادة فتحه
                if "session" in str(e).lower() or "disconnected" in str(e).lower():
                    print(f"🔄 {panel_name}: Browser disconnected, restarting...")
                    break 
                await asyncio.sleep(15)
                
    except Exception as e:
        error_msg = f"❌ **{panel_name} CRASHED**\n`{str(e)}`"
        print(error_msg)
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
        # إعادة تشغيل السكرابينج في حالة الانهيار بعد فترة
        await asyncio.sleep(30)
        await scrape_panel(account)

# ==========================================
# Main
# ==========================================
async def main():
    print(f"Starting {len(ACCOUNTS)} panels...")
    print(f"Sending to Telegram ID: {TARGET_TELEGRAM_ID}")
    
    tasks = [scrape_panel(acc) for acc in ACCOUNTS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main())
