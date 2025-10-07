import os
import re
import time
import requests
from bs4 import BeautifulSoup
from telegram import Bot
import phonenumbers
from emoji_country_flag import country_flag

# === CONFIG ===
TELEGRAM_TOKEN = os.getenv("TELEGRAM_TOKEN", "7142079092:AAFhG0yj_XArF2OOv1vWRR5z2rW9tL8Rtw8")
CHAT_ID = os.getenv("CHAT_ID", "6006322754")

LOGIN_PAGE_URL = "http://109.236.84.81/ints/login"
LOGIN_POST_URL = "http://109.236.84.81/ints/signin"
API_URL = "http://109.236.84.81/ints/agent/res/data_smscdr.php?fdate1=2025-10-07%2000%3A00%3A00&fdate2=2025-10-07%2023%3A59%3A59&frange=&fclient=&fnum=&fcli=&fgdate=&fgmonth=&fgrange=&fgclient=&fgnumber=&fgcli=&fg=0&sEcho=1&iColumns=9&sColumns=%2C%2C%2C%2C%2C%2C%2C%2C%2C&iDisplayStart=0&iDisplayLength=25&mDataProp_0=0&sSearch_0=&bRegex_0=false&bSearchable_0=true&bSortable_0=true&mDataProp_1=1&sSearch_1=&bRegex_1=false&bSearchable_1=true&bSortable_1=true&mDataProp_2=2&sSearch_2=&bRegex_2=false&bSearchable_2=true&bSortable_2=true&mDataProp_3=3&sSearch_3=&bRegex_3=false&bSearchable_3=true&bSortable_3=true&mDataProp_4=4&sSearch_4=&bRegex_4=false&bSearchable_4=true&bSortable_4=true&mDataProp_5=5&sSearch_5=&bRegex_5=false&bSearchable_5=true&bSortable_5=true&mDataProp_6=6&sSearch_6=&bRegex_6=false&bSearchable_6=true&bSortable_6=true&mDataProp_7=7&sSearch_7=&bRegex_7=false&bSearchable_7=true&bSortable_7=true&mDataProp_8=8&sSearch_8=&bRegex_8=false&bSearchable_8=false&sSearch=&bRegex=false&iSortCol_0=0&sSortDir_0=desc&iSortingCols=1"

USERNAME = os.getenv("SMS_USER", "Fehadofficial")
PASSWORD = os.getenv("SMS_PASS", "Fehad@1122")

# === INIT ===
session = requests.Session()
bot = Bot(token=TELEGRAM_TOKEN)

last_id = None


# Extract OTP
def extract_otp(text):
    if not text:
        return None
    m = re.search(r"\b\d{4,8}\b", text)
    return m.group(0) if m else None


# Detect Country
def get_country_info(number):
    try:
        num = phonenumbers.parse(str(number), None)
        iso = phonenumbers.region_code_for_number(num)
        if iso:
            return f"{iso} {country_flag(iso)}"
    except Exception:
        return "Unknown 🌍"
    return "Unknown 🌍"


# Map API row
def map_row(row):
    return {
        "id": row[0],
        "date": row[0],
        "number": row[2],
        "cli": row[3],
        "client": row[4],
        "message": row[5],
        "country": get_country_info(row[2])
    }


# Send Telegram
def send_telegram_sms(sms):
    otp = extract_otp(sms["message"]) or "N/A"
    final = f"""<b>{sms['country']} {sms['cli']} OTP Received...</b>

📞 <b>Number:</b> <code>{sms['number']}</code>
🔑 <b>OTP:</b> <code>{otp}</code>
🌍 <b>Country:</b> {sms['country']}
📱 <b>Service:</b> {sms['cli']}
📆 <b>Date:</b> {sms['date']}

💬 <b>Full SMS:</b>
<pre>{sms['message']}</pre>
"""
    bot.send_message(chat_id=CHAT_ID, text=final, parse_mode="HTML")
    print("✅ Sent:", sms["id"], "->", sms["country"], "OTP:", otp)


# Login with captcha
def perform_login():
    print("🔐 GET login page...")
    r = session.get(LOGIN_PAGE_URL, headers={"User-Agent": "Mozilla/5.0"})
    soup = BeautifulSoup(r.text, "html.parser")
    text = soup.get_text()

    captcha_answer = None
    match = re.search(r"What is\s*([\-]?\d+)\s*([\+\-\*xX\/])\s*([\-]?\d+)", text)
    if match:
        a, op, b = int(match.group(1)), match.group(2), int(match.group(3))
        if op in ["+", "-"]:
            captcha_answer = str(a + b) if op == "+" else str(a - b)
        elif op in ["*", "x", "X"]:
            captcha_answer = str(a * b)
        elif op == "/" and b != 0:
            captcha_answer = str(a // b)

    data = {"username": USERNAME, "password": PASSWORD}
    if captcha_answer:
        data["capt"] = captcha_answer

    res = session.post(LOGIN_POST_URL, data=data, headers={"User-Agent": "Mozilla/5.0"}, allow_redirects=True)
    return res.status_code in [200, 302]


# Fetch SMS
def fetch_sms_api():
    try:
        res = session.get(API_URL, headers={"X-Requested-With": "XMLHttpRequest", "User-Agent": "Mozilla/5.0"})
        return res.json()
    except Exception as e:
        print("Fetch SMS error:", e)
        return None


# Worker
def start_worker():
    global last_id
    if not perform_login():
        print("❌ Login failed")
        return

    data = fetch_sms_api()
    if data and "aaData" in data and len(data["aaData"]) > 0:
        latest = map_row(data["aaData"][0])
        last_id = latest["id"]
        send_telegram_sms(latest)
    else:
        print("No SMS found initially.")

    while True:
        time.sleep(10)
        d = fetch_sms_api()
        if not d or "aaData" not in d or len(d["aaData"]) == 0:
            continue
        latest = map_row(d["aaData"][0])
        if latest["id"] != last_id:
            last_id = latest["id"]
            send_telegram_sms(latest)


if __name__ == "__main__":
    start_worker()
