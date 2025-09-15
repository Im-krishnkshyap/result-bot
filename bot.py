import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

TARGET_MARKET = " SHRI GANESH "
LAST_RESULT_FILE = "last_result.txt"  # last result cache

if not BOT_TOKEN or not CHAT_ID or not URL:
    raise ValueError("⚠️ BOT_TOKEN, GROUP_CHAT_ID, और TARGET_URL सेट करें!")

def scrape_results():
    try:
        r = requests.get(URL, timeout=10)
        r.raise_for_status()
    except requests.RequestException as e:
        return None, f"❌ रिज़ल्ट लाने में दिक्कत: {e}"

    soup = BeautifulSoup(r.text, "html.parser")
    games = soup.find_all("p", class_="livegame")

    for game in games:
        market = game.get_text(strip=True)
        result_tag = game.find_next_sibling("p", class_="liveresult")
        result = result_tag.get_text(strip=True) if result_tag else "WAIT"

        if market.upper() == TARGET_MARKET.upper():
            return result, f"{market} === {result}"

    return None, f"⚠️ {TARGET_MARKET} का रिज़ल्ट नहीं मिला!"

def load_last_result():
    if os.path.exists(LAST_RESULT_FILE):
        with open(LAST_RESULT_FILE, "r", encoding="utf-8") as f:
            return f.read().strip()
    return None

def save_last_result(result):
    with open(LAST_RESULT_FILE, "w", encoding="utf-8") as f:
        f.write(result)

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    for i in range(0, len(msg), 4000):  # telegram 4096 char limit
        part = msg[i:i+4000]
        requests.post(api, data={"chat_id": CHAT_ID, "text": part})

if __name__ == "__main__":
    result, message = scrape_results()
    last_result = load_last_result()

    if result and result != "WAIT" and result != last_result:
        final_text = f"📢 खबर की जानकारी👇\n\n{message}\n\n🙏 Antaryami Baba"
        send_message(final_text)
        save_last_result(result)
        print("✅ नया रिज़ल्ट भेजा गया:", result)
    else:
        print("⏳ अभी नया रिज़ल्ट available नहीं है।")
