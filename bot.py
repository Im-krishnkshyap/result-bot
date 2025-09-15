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

# अगर आप नहीं चाहते कि पहला रन message भेजे, True रखें
SKIP_FIRST_SEND = True

def normalize_text(s):
    if s is None:
        return ""
    # collapse whitespace, strip, uppercase — ताकि hidden differences न गिनें
    return " ".join(s.split()).upper()

def load_history():
    try:
        if os.path.exists(HISTORY_FILE):
            with open(HISTORY_FILE, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        print("⚠️ load_history error:", e)
    return {}

def save_history(data):
    try:
        with open(HISTORY_FILE, "w", encoding="utf-8") as f:
            json.dump(data, f, ensure_ascii=False, indent=2)
    except Exception as e:
        print("⚠️ save_history error:", e)

def scrape_results():
    try:
        r = requests.get(URL, timeout=10)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")
    except Exception as e:
        print("❌ Request/Parsing error:", e)
        return {}

    current_results = {}
    games = soup.find_all("p", class_="livegame")
    for game in games:
        market_raw = game.get_text(strip=True)
        market = normalize_text(market_raw)

        result_tag = game.find_next_sibling("p", class_="liveresult")
        result_raw = result_tag.get_text(strip=True) if result_tag else "WAIT"
        result = normalize_text(result_raw)

        # normalize TARGET_MARKETS too for matching
        for t in TARGET_MARKETS:
            if normalize_text(t) == market:
                current_results[t] = result  # store with original TARGET_MARKET name (keeps message pretty)
                break

    return current_results

def diff_results(last, current):
    last_keys = set(last.keys())
    cur_keys = set(current.keys())

    added = cur_keys - last_keys
    removed = last_keys - cur_keys
    changed = set(k for k in (last_keys & cur_keys) if last.get(k) != current.get(k))
    return {
        "added": sorted(list(added)),
        "removed": sorted(list(removed)),
        "changed": sorted(list(changed))
    }

def format_message(current, last, diffs):
    lines = []
    if diffs["added"] or diffs["removed"] or diffs["changed"]:
        lines.append("🆕 *Update आया है!*")
    lines.append("*🔛खबर की जानकारी👉*")
    lines.append("*✴️🆗️✴️♻️™️©️✅️*")

    # current results (mark new/changed)
    for market, result in current.items():
        mark = ""
        if market in diffs["added"]:
            mark = " 🆕"
        elif market in diffs["changed"]:
            mark = " 🔁"
        lines.append(f"*{market} =={result}*{mark}")

    # removed (strike-through)
    for market in diffs["removed"]:
        prev_val = last.get(market, "")
        # Telegram Markdown supports ~strike~ in MarkdownV2, but using simple ~...~ often works too.
        lines.append(f"~{market} =={prev_val}~")

    lines.append("✅️✅️✅️✅️✅️✅️✅️✅️")
    lines.append("*AAP KA 🕉Antaryami Baba🕉*")
    return "\n".join(lines)

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        resp = requests.post(api, data=data, timeout=10)
        if resp.status_code != 200:
            print("❌ Telegram API returned", resp.status_code, resp.text)
    except Exception as e:
        print("❌ send_message error:", e)

if __name__ == "__main__":
    # Load once
    last_results = load_history()

    # If no history and SKIP_FIRST_SEND True, create initial snapshot and do not send message
    if SKIP_FIRST_SEND and not last_results:
        print("ℹ️ No history found — taking initial snapshot and will NOT send on first run.")
        last_results = scrape_results()
        save_history(last_results)

    print("▶️ Starting loop. history file:", os.path.abspath(HISTORY_FILE))
    while True:
        try:
            current_results = scrape_results()

            # debug: show repr to catch hidden chars if needed
            print("DEBUG last:", last_results)
            print("DEBUG current:", current_results)

            diffs = diff_results(last_results, current_results)
            if diffs["added"] or diffs["removed"] or diffs["changed"]:
                print("🔔 Change detected:", diffs)
                text = format_message(current_results, last_results, diffs)
                send_message(text[:4000])
                save_history(current_results)
                last_results = current_results
            else:
                print("⏳ No change.")

        except Exception as e:
            print("❌ Loop error:", e)

        time.sleep(5)
