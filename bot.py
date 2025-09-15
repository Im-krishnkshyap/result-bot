import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

# यहाँ अपने target नाम डालें
TARGET_MARKET = "N C R"

def scrape_results():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    results = []

    # सभी livegame tags ढूँढो
    games = soup.find_all("p", class_="livegame")
    for game in games:
        market = game.get_text(strip=True)

        # अगला sibling result पकड़ना
        result_tag = game.find_next_sibling("p", class_="liveresult")
        result = result_tag.get_text(strip=True) if result_tag else "WAIT"

        # सिर्फ target नाम match होने पर ही जोड़ना
        if market.upper() == TARGET_MARKET.upper():
            results.append(f"{market} === {result}")

    if not results:
        return f"⚠️ {TARGET_MARKET} का रिज़ल्ट नहीं मिला!"

    # टेक्स्ट तैयार करना
    final_text = "📢 खबर की जानकारी👇\n\n"
    final_text += "\n".join(results)
    final_text += "\n\n🙏 Antaryami Baba"

    return final_text

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(api, data=data)

if __name__ == "__main__":
    text = scrape_results()
    send_message(text[:4000])
