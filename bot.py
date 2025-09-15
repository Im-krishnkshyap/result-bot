import os
import time
import json
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

HISTORY_FILE = "last_results.json"

# Multiple target markets
TARGET_MARKETS = [
    "DELHI BAZAR (DL)", "DELHI DREAM", "SUNDRAM", "PESHAWAR", "TAJ"
]

def load_history():
    if os.path.exists(HISTORY_FILE):
        with open(HISTORY_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    return {}

def save_history(data):
    with open(HISTORY_FILE, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)

def scrape_results():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    current_results = {}
    games = soup.find_all("p", class_="livegame")
    for game in games:
        market = game.get_text(strip=True)
        result_tag = game.find_next_sibling("p", class_="liveresult")
        result = result_tag.get_text(strip=True) if result_tag else "WAIT"

        if market in TARGET_MARKETS:
            current_results[market] = result

    return current_results

def format_message(current_results, last_results):
    lines = []
    lines.append("*🔛खबर की जानकारी👉*")
    lines.append("*✴️🆗️✴️♻️™️©️✅️*")

    # अभी के results
    for market, result in current_results.items():
        lines.append(f"*{market} =={result}*")

    # पुराने लेकिन अब गायब results
    for market, result in last_results.items():
        if market not in current_results:
            lines.append(f"~{market} =={result}~")

    lines.append("✅️✅️✅️✅️✅️✅️✅️✅️")
    lines.append("*AAP KA 🕉Antaryami Baba🕉*")

    return "\n".join(lines)

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(api, data=data)

if __name__ == "__main__":
    while True:
        try:
            last_results = load_history()
            current_results = scrape_results()

            # ⚡ सिर्फ update पर ही भेजना
            if current_results != last_results:
                text = format_message(current_results, last_results)
                send_message(text[:4000])
                save_history(current_results)
                print("🔔 नया update मिला, message भेजा गया।")
            else:
                print("⏳ कोई update नहीं।")

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(5)  # हर 5 सेकंड बाद चेक करेगा
