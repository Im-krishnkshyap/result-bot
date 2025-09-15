import os
import time
import json
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

HISTORY_FILE = "last_results.json"
TARGET_MARKETS = [
    "DELHI BAZAR (DL)", "DELHI DREAM", "SUNDRAM", "PESHAWAR", "TAJ"
]

def normalize_text(s: str) -> str:
    """Whitespace + case normalize, ताकि छोटे फर्क न गिने जाएँ"""
    return " ".join(s.split()).upper() if s else ""

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
        market_raw = game.get_text(strip=True)
        market = normalize_text(market_raw)

        result_tag = game.find_next_sibling("p", class_="liveresult")
        result_raw = result_tag.get_text(strip=True) if result_tag else "WAIT"
        result = normalize_text(result_raw)

        for t in TARGET_MARKETS:
            if normalize_text(t) == market:
                current_results[t] = result
                break

    return current_results

def diff_results(last, current):
    """Added / Removed / Changed markets निकालो"""
    last_keys = set(last.keys())
    cur_keys = set(current.keys())

    added = cur_keys - last_keys
    removed = last_keys - cur_keys
    changed = {k for k in (last_keys & cur_keys) if last.get(k) != current.get(k)}

    return {"added": added, "removed": removed, "changed": changed}

def format_message(current, last, diffs):
    lines = []
    lines.append("*🔛खबर की जानकारी👉*")
    lines.append("*✴️🆗️✴️♻️™️©️✅️*")

    # Current results
    for market, result in current.items():
        mark = ""
        if market in diffs["added"]:
            mark = " 🆕"
        elif market in diffs["changed"]:
            mark = " 🔁"
        lines.append(f"*{market} =={result}*{mark}")

    # Removed markets
    for market in diffs["removed"]:
        prev_val = last.get(market, "")
        lines.append(f"~{market} =={prev_val}~")

    lines.append("✅️✅️✅️✅️✅️✅️✅️✅️")
    lines.append("*AAP KA 🕉Antaryami Baba🕉*")
    return "\n".join(lines)

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    r = requests.post(api, data=data, timeout=10)
    if r.status_code != 200:
        print("❌ Telegram error:", r.text)

if __name__ == "__main__":
    last_results = load_history()

    while True:
        try:
            current_results = scrape_results()
            diffs = diff_results(last_results, current_results)

            if diffs["added"] or diffs["removed"] or diffs["changed"] or not last_results:
                text = format_message(current_results, last_results, diffs)
                send_message(text[:4000])
                save_history(current_results)
                last_results = current_results
                print("🔔 Message sent:", diffs)
            else:
                print("⏳ कोई बदलाव नहीं मिला")

        except Exception as e:
            print("❌ Error:", e)

        time.sleep(5)
