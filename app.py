import os
import re
import time
import requests
from bs4 import BeautifulSoup
import phonenumbers
from phonenumbers import geocoder
import emoji
from telegram import Bot

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7142079092:AAFhG0yj_XArF2OOv1vWRR5z2rW9tL8Rtw8")
CHAT_ID = os.getenv("CHAT_ID", "6006322754")

LOGIN_PAGE_URL = "http://109.236.84.81/ints/login"
LOGIN_POST_URL = "http://109.236.84.81/ints/signin"
API_URL = (
    "http://109.236.84.81/ints/agent/res/data_smscdr.php"
    "?fdate1=2025-10-07%2000%3A00%3A00&fdate2=2025-10-07%2023%3A59%3A59"
    "&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0"
    "&sEcho=1&iColumns=9&sColumns=%2C%2C%2C%2C%2C%2C%2C%2C%2C&iDisplayStart=0&iDisplayLength=25"
    "&mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true"
    "&mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true"
    "&mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true"
    "&mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true"
    "&mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true"
    "&mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true"
    "&mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true"
    "&mDataProp_7=7&sSearch_7=&bRegex_7=false&bSearchable_7=true&bSortable_7=true"
    "&mDataProp_8=8&sSearch_8=&bRegex_8=false&bSearchable_8=false&sSearch=&bRegex=false"
    "&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1"
)

USERNAME = os.getenv("SMS_USER", "Fehadofficial")
PASSWORD = os.getenv("SMS_PASS", "Fehad@1122")

# === INIT ===
session = requests.Session()
bot = Bot(token=TELEGRAM_TOKEN)
last_id = None


def extract_otp(text):
    """Extract OTP from text"""
    if not text:
        return None
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None


def get_country_info(number):
    """Get country from phone number"""
    try:
        s = str(number).strip().replace(" ", "")
        if s.startswith("00"):
            s = "+" + s[2:]
        if not s.startswith("+"):
            s = "+" + s
        phone = phonenumbers.parse(s, None)
        country_name = geocoder.country_name_for_number(phone, "en")
        if not country_name:
            return "Unknown 🌍"
        return f"{country_name}"
    except Exception:
        return "Unknown 🌍"


def map_row(row):
    return {
        "id": row[0],
        "date": row[0],
        "number": row[2],
        "cli": row[3],
        "client": row[4],
        "message": row[5],
        "country": get_country_info(row[2]),
    }


def send_telegram_sms(sms):
    otp = extract_otp(sms["message"]) or "N/A"
    final = f"""<b>{sms['country']} {sms['cli']} OTP Received...</b>

📞 <b>Number:</b> <code>{sms['number']}</code>
🔑 <b>𝐘𝐨𝐮𝐫 𝐎𝐓𝐏:</b> <code>{otp}</code>
🌍 <b>𝐂𝐨𝐮𝐧𝐭𝐫𝐲:</b> {sms['country']}
📱 <b>𝐒𝐞𝐫𝐯𝐢𝐜𝐞:</b> {sms['cli']}
📆 <b>❝𝐃𝐚𝐭𝐞❞:</b> {sms['date']}

💬 <b>𝐅𝐮𝐥𝐥 𝐒𝐌𝐒:</b>
<pre>{sms['message']}</pre>
"""
    try:
        bot.send_message(CHAT_ID, final, parse_mode="HTML")
        print(f"✅ Sent: {sms['id']} -> {sms['country']} OTP: {otp}")
    except Exception as e:
        print("Telegram send error:", str(e))


def perform_login_and_save_cookies():
    """Login with captcha"""
    try:
        print("🔐 GET login page...")
        res = session.get(LOGIN_PAGE_URL, headers={"User-Agent": "Mozilla/5.0"})
        soup = BeautifulSoup(res.text, "html.parser")
        body_text = soup.get_text()

        # parse captcha
        captcha_answer = None
        m = re.search(r"What is\s*([\-]?\d+)\s*([\+\-\*xX/])\s*([\-]?\d+)", body_text)
        if m:
            a, op, b = int(m.group(1)), m.group(2), int(m.group(3))
            if op == "+":
                captcha_answer = str(a + b)
            elif op == "-":
                captcha_answer = str(a - b)
            elif op in ["*", "x", "X"]:
                captcha_answer = str(a * b)
            elif op == "/" and b != 0:
                captcha_answer = str(a // b)
            print("Detected captcha:", m.group(0), "=>", captcha_answer)

        data = {
            "username": USERNAME,
            "password": PASSWORD,
        }
        if captcha_answer:
            data["capt"] = captcha_answer

        # include hidden inputs
        for inp in soup.select("form input[type=hidden]"):
            if inp.get("name") not in ["username", "password", "capt"]:
                data[inp.get("name")] = inp.get("value", "")

        post_res = session.post(LOGIN_POST_URL, data=data, headers={
            "Content-Type": "application/x-www-form-urlencoded",
            "Origin": "http://109.236.84.81",
            "Referer": LOGIN_PAGE_URL,
            "User-Agent": "Mozilla/5.0",
        }, allow_redirects=False)

        print("Login POST status:", post_res.status_code)
        if post_res.status_code in [302, 303]:
            return True
        if "Login" not in post_res.text:
            return True
        print("❌ Login failed, got login page again.")
        return False
    except Exception as e:
        print("Login error:", str(e))
        return False


def fetch_sms_api():
    try:
        res = session.get(API_URL, headers={
            "User-Agent": "Mozilla/5.0",
            "X-Requested-With": "XMLHttpRequest",
            "Accept": "application/json, text/javascript, */*; q=0.01",
            "Referer": "http://109.236.84.81/ints/agent/SMSCDRReports",
        })
        return res.json()
    except Exception as e:
        print("Fetch SMS API error:", str(e))
        return None


def start_worker():
    global last_id
    if not perform_login_and_save_cookies():
        print("Login failed — aborting.")
        return

    data = fetch_sms_api()
    if data and isinstance(data.get("aaData"), list) and len(data["aaData"]) > 0:
        latest = map_row(data["aaData"][0])
        last_id = latest["id"]
        send_telegram_sms(latest)
    else:
        print("No SMS found initially.")

    while True:
        d = fetch_sms_api()
        if not d or not isinstance(d.get("aaData"), list) or len(d["aaData"]) == 0:
            time.sleep(10)
            continue
        latest = map_row(d["aaData"][0])
        if latest["id"] != last_id:
            last_id = latest["id"]
            send_telegram_sms(latest)
        time.sleep(10)


if __name__ == "__main__":
    start_worker()
