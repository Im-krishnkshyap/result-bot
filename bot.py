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

        # Example: पूरे पेज का टेक्स्ट भेजना
        text = soup.get_text(strip=True)

        # खाली ना हो तो Telegram पर भेज दो
        if text:
            send_message(text[:4000])  # Telegram limit 4096 है
        else:
            send_message("⚠️ कोई डेटा नहीं मिला")
    except Exception as e:
        send_message(f"❌ Error: {e}")

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(api, data=data)

if __name__ == "__main__":
    scrape_and_send()
