import os
import time
import requests
from bs4 import BeautifulSoup

# अपनी Telegram bot की जानकारी भरो
BOT_TOKEN = os.getenv("BOT_TOKEN")         # या सीधा "123456:ABCDEF..."
CHAT_ID = os.getenv("GROUP_CHAT_ID")       # या सीधा "-1001234567890"
URL = os.getenv("TARGET_URL")              # result वाली site

TARGET_MARKET = "HINDUSTAN"   # सिर्फ इसी का result चाहिए
last_result = None            # पिछला result save रहेगा

def normalize_text(s: str) -> str:
    return " ".join(s.split()).upper() if s else ""

def scrape_result():
    """एक market का result scrape करो"""
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    games = soup.find_all("p", class_="livegame")

    for game in games:
        market_raw = game.get_text(strip=True)
        market = normalize_text(market_raw)

        if market == normalize_text(TARGET_MARKET):
            result_tag = game.find_next_sibling("p", class_="liveresult")
            result_raw = result_tag.get_text(strip=True) if result_tag else "WAIT"
            return result_raw.strip()

    return None  # market नहीं मिला

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    r = requests.post(api, data=data, timeout=10)
    if r.status_code != 200:
        print("❌ Telegram error:", r.text)

if __name__ == "__main__":
    global last_result

    while True:
        try:
            current_result = scrape_result()
            if current_result is None:
                print("⏳ Market नहीं मिला")
            elif current_result != last_result:
                msg = f"*{TARGET_MARKET} == {current_result}*"
                send_message(msg)
                print("🔔 Sent:", msg)
                last_result = current_result
            else:
                print("⏳ कोई बदलाव नहीं मिला")
        except Exception as e:
            print("❌ Error:", e)

        time.sleep(5)  # हर 5 सेकंड बाद चेक करेगा
