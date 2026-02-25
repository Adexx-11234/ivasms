import asyncio
import re
from datetime import datetime
from telethon import TelegramClient
import nodriver as uc
import os
import json
import sys
import random

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
PROXY_PORT = "4950"
PROXY_USER = "Samy1gnQL2801-zone-abc-region-ci"
PROXY_PASS = "q0OQGgu6ec"

IVASMS_LOGIN_URL = "https://ivasms.com/login"
IVASMS_LIVE_URL = "https://www.ivasms.com/portal/live/my_sms"

PROCESSED_SIGNATURES = set()

USER_AGENTS = [
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/122.0.0.0 Safari/537.36",
    "Mozilla/5.0 (Macintosh; Intel Mac OS X 10_15_7) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/121.0.0.0 Safari/537.36"
]

print("DEBUG: Starting Telegram Client...", flush=True)
bot = TelegramClient('ivasms_scraper_bot', API_ID, API_HASH).start(bot_token=BOT_TOKEN)
print("DEBUG: Telegram Client Started.", flush=True)

async def scrape_panel(account):
    panel_name = account['name']
    email = account['email']
    password = account['pass']
    
    while True:
        browser = None
        try:
            print(f"🚀 {panel_name}: Starting nodriver with Proxy...", flush=True)
            
            ua = random.choice(USER_AGENTS)
            # تنسيق البروكسي لـ nodriver
            proxy_arg = f"--proxy-server=http://{PROXY_HOST}:{PROXY_PORT}"
            
            browser = await uc.start(
                headless=True, 
                browser_args=[
                    "--no-sandbox", 
                    "--disable-dev-shm-usage", 
                    "--disable-gpu",
                    f"--user-agent={ua}",
                    proxy_arg,
                    "--disable-blink-features=AutomationControlled"
                ]
            )
            
            # التعامل مع مصادقة البروكسي (Proxy Auth)
            page = await browser.get("https://api.ipify.org") # صفحة بسيطة لاختبار البروكسي أولاً
            await asyncio.sleep(5)
            
            # ملاحظة: nodriver يتعامل مع Proxy Auth عبر المتصفح إذا ظهرت نافذة المصادقة
            # ولكن الأفضل استخدام بروكسي بدون مصادقة أو IP-Whitelisted إذا أمكن.
            # سنحاول الدخول مباشرة للموقع الآن.
            
            print(f"🌍 {panel_name}: Navigating to login page via Proxy...", flush=True)
            page = await browser.get(IVASMS_LOGIN_URL)
            
            wait_time = random.randint(20, 35)
            print(f"DEBUG: {panel_name} Waiting {wait_time}s for Cloudflare...", flush=True)
            await asyncio.sleep(wait_time) 
            
            email_field = await page.select('input[name="email"]', timeout=60)
            
            if not email_field:
                print(f"❌ {panel_name}: Could not find login fields (Still Blocked or Proxy Auth Issue)", flush=True)
                raise Exception("Cloudflare Blocked")

            print(f"📝 {panel_name}: Entering credentials...", flush=True)
            await email_field.send_keys(email)
            await asyncio.sleep(random.uniform(1, 3))
            
            pass_field = await page.select('input[name="password"]')
            await pass_field.send_keys(password)
            await asyncio.sleep(random.uniform(1, 2))
            
            login_btn = await page.select('button[type="submit"]')
            await login_btn.click()
            
            print(f"DEBUG: {panel_name} Waiting for redirect...", flush=True)
            await asyncio.sleep(20)
            
            if "portal" not in page.url:
                print(f"⚠️ {panel_name}: Login failed, current URL: {page.url}", flush=True)
                await asyncio.sleep(10)
                if "portal" not in page.url:
                    raise Exception("Login failed")

            print(f"✅ {panel_name}: Login successful", flush=True)
            await bot.send_message(TARGET_TELEGRAM_ID, f"✅ **{panel_name} started monitoring (Proxy Active)**")
            
            await page.get(IVASMS_LIVE_URL)
            await asyncio.sleep(15)

            while True:
                try:
                    await page.reload()
                    await asyncio.sleep(15)
                    rows = await page.select_all('table tbody tr')
                    
                    for row in rows[:10]:
                        try:
                            cols = await row.select_all('td')
                            if len(cols) >= 5:
                                phone = (await cols[0].get_text()).strip()
                                service = (await cols[1].get_text()).strip()
                                message = (await cols[4].get_text()).strip()
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
                    await asyncio.sleep(30)
                except Exception as e:
                    print(f"⚠️ {panel_name} Loop Error: {e}", flush=True)
                    break 
        except Exception as e:
            print(f"❌ {panel_name} CRASHED: {e}", flush=True)
        finally:
            if browser:
                try: await asyncio.wait_for(browser.stop(), timeout=10)
                except: pass
            print(f"🔄 {panel_name}: Restarting in 60 seconds...", flush=True)
            await asyncio.sleep(60)

async def main():
    tasks = [scrape_panel(acc) for acc in ACCOUNTS]
    await asyncio.gather(*tasks)

if __name__ == '__main__':
    with bot:
        bot.loop.run_until_complete(main())
