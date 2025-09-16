import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime

BOT_TOKEN = os.getenv("BOT_TOKEN")        # Telegram bot token
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")  # Telegram group chat id
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

# ------------------ Utility ------------------

def canonical_name(raw):
    s = raw.upper().strip()
    if "DELHI BAZAR" in s: return "DELHI BAZAR"
    if "SHRI" in s and "GANESH" in s: return "SHRI GANESH"
    if "FARIDABAD" in s: return "FARIDABAD"
    if "GHAZI" in s or "GAZI" in s: return "GHAZIYABAD"
    if "GALI" in s: return "GALI"
    if "DISAWER" in s or "DESAWAR" in s: return "DISAWER"
    return s

def extract_num(text):
    t = text.strip()
    if t.upper() == "WAIT" or t == "":
        return None
    return t if t.isdigit() else None

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_html():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def send_message(text):
    if BOT_TOKEN and GROUP_CHAT_ID:
        url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
        resp = requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text})
        print("Message sent:", resp.status_code)
    else:
        print("BOT_TOKEN or GROUP_CHAT_ID not set!")

# ------------------ Parsing ------------------

def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        cname = canonical_name(g.get_text())
        if cname in TARGETS and i < len(vals):
            num = extract_num(vals[i].get_text())
            results[cname] = num if num else "WAIT"
    return results

def build_message(updates):
    lines = [f"🕉 Antaryami Baba 🕉:"]
    now = datetime.now().strftime("%d-%m %I:%M %p")
    lines.append(f"📅 {now} का अपडेट")
    for g, v in updates.items():
        lines.append(f"{g} → {v}")
    return "\n".join(lines)

# ------------------ Main ------------------

def main():
    state = load_state()
    soup = fetch_html()
    live_results = parse_live(soup)

    updates = {}
    for g in TARGETS:
        val = live_results.get(g, "WAIT")
        # अगर नया result आया या state में नहीं है
        if state.get(g) != val:
            updates[g] = val
            state[g] = val

    if updates:
        msg = build_message(updates)
        send_message(msg)
        save_state(state)
    else:
        print("No new updates.")

if __name__ == "__main__":
    main()
