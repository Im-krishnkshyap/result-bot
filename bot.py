import os
import json
import requests
from datetime import datetime, time
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

# Time windows (24h) - adjust as per your schedule
REFRESH_WINDOWS = {
    "DELHI BAZAR": (time(3,14), time(3,20)),
    "SHRI GANESH": (time(4,45), time(4,50)),
    "FARIDABAD": (time(6,14), time(6,20)),
    "GHAZIYABAD": (time(10,5), time(10,15)),
    "GALI": (time(12,0), time(12,5)),
    "DISAWER": (time(17,15), time(17,20)),
}

# ---------------- Utility ----------------
def load_state():
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE, "r") as f:
                return json.load(f)
        except:
            pass
    return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_html():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text})

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
        return "WAIT"
    return t if t.isdigit() else "WAIT"

def in_window(game):
    now = datetime.now().time()
    start, end = REFRESH_WINDOWS[game]
    return start <= now <= end

def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        cname = canonical_name(g.get_text())
        if cname in TARGETS and i < len(vals):
            num = extract_num(vals[i].get_text())
            results[cname] = num
    return results

def build_message(updates):
    lines = ["🕉Antaryami Baba🕉:"]
    lines.append(f"📅 {datetime.now().strftime('%d-%m')} का अपडेट")
    for g, v in updates.items():
        lines.append(f"{g} → {v}")
    return "\n".join(lines)

# ---------------- Main ----------------
def main():
    state = load_state()
    soup = fetch_html()
    live_results = parse_live(soup)

    updates = {}
    for g in TARGETS:
        if in_window(g):
            val = live_results.get(g, "WAIT")
            print(f"[DEBUG] {g}: {val}")  # debug
            if state.get(g) != val:
                updates[g] = val
                state[g] = val

    if updates:
        msg = build_message(updates)
        send_message(msg)
        save_state(state)

if __name__ == "__main__":
    main()
