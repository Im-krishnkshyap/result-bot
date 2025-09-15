import os
import json
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

HISTORY_FILE = "last_results.json"

# Multiple target markets
TARGET_MARKETS = ["DELHI BAZAR (DL)", "DELHI DREAM", "SUNDRAM", "PESHAWAR", "TAJ", "SUNDRAM"]

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

    # अभी के results
    current_results = {}

    games = soup.find_all("p", class_="livegame")
    for game in games:
        market = game.get_text(strip=True)
        result_tag = game.find_next_sibling("p", class_="liveresult")
        result = result_tag.get_text(strip=True) if result_tag else "WAIT"

        if market in TARGET_MARKETS:
            current_results[market] = result

    # पुराने results load
    last_results = load_history()

    # message बनाना
    lines = []
    lines.append("*🔛खबर की जानकारी👉*")
    lines.append("*✴️🆗️✴️♻️™️©️✅️*")

    # पहले current वाले
    for market, result in current_results.items():
        lines.append(f"*{market} =={result}*")

    # अब जो गायब हो गए (last में थे लेकिन अब नहीं हैं)
    for market, result in last_results.items():
        if market not in current_results:
            lines.append(f"~{market} =={result}~")  # strike-through दिखेगा Telegram Markdown में

    lines.append("✅️✅️✅️✅️✅️✅️✅️✅️")
    lines.append("*AAP KA 🕉Antaryami Baba🕉*")

    # history update
    save_history(current_results)

    return "\n".join(lines)

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    requests.post(api, data=data)

if __name__ == "__main__":
    text = scrape_results()
    send_message(text[:4000])
