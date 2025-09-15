import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

def scrape_and_send():
    try:
        r = requests.get(URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        # 👉 सिर्फ रिज़ल्ट का हिस्सा निकालें
        result_box = soup.select_one("div.liveresult")  # सही selector डालना होगा
        if result_box:
            text = result_box.get_text(strip=True)
        else:
            text = "⚠️ रिज़ल्ट नहीं मिला"

        send_message(text[:4000])  # Telegram limit
    except Exception as e:
        send_message(f"❌ Error: {e}")

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(api, data=data)

if __name__ == "__main__":
    scrape_and_send()
