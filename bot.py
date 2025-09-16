import os
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"

# Target games
TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

# ------------------ Utility ------------------

def canonical_name(raw):
    s = raw.upper().strip()
    if "DELHI BAZAR" in s: return "DELHI BAZAR"
    if "SHRI" in s and "GANESH" in s: return "SHRI GANESH"
    if "FARIDABAD" in s: return "FARIDABAD"
    if "GHAZI" in s or "GAZI" in s: return "GHAZIYABAD"
    if "GALI" == s: return "GALI"
    if "DISAWER" in s or "DESAWAR" in s: return "DISAWER"
    return s

def fetch_html():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"date": None, "sent_results": {}}
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"date": None, "sent_results": {}}
            if "date" not in data or "sent_results" not in data:
                return {"date": None, "sent_results": {}}
            return data
    except Exception:
        return {"date": None, "sent_results": {}}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text})

# ------------------ Live Parsing ------------------

def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        cname = canonical_name(g.get_text())
        if cname in TARGETS and i < len(vals):
            val_text = vals[i].get_text().strip()
            if val_text.upper() != "WAIT" and val_text != "":
                results[cname] = val_text  # केवल valid numbers add करें
    return results

def build_message(date_str, results):
    lines = [f"📅 {date_str} का अपडेट"]
    for g in TARGETS:
        if g in results:
            lines.append(f"{g} → {results[g]}")
        else:
            lines.append(f"{g} → WAIT")
    return "\n".join(lines)

# ------------------ Main ------------------

def main():
    today = datetime.now().strftime("%d-%m")
    state = load_state()
    if "date" not in state: state["date"] = None
    if "sent_results" not in state: state["sent_results"] = {}

    soup = fetch_html()
    live_results = parse_live(soup)

    # अगर date change हुआ → state reset
    if state["date"] != today:
        state = {"date": today, "sent_results": {}}
        save_state(state)

    # अपडेट्स निकालो
    updates = {}
    for g, val in live_results.items():
        prev_val = state.get("sent_results", {}).get(g)
        if prev_val != val:
            updates[g] = val

    # अगर कोई update है → भेजो
    if updates:
        msg = build_message(today, updates)
        send_message(msg)
        state.setdefault("sent_results", {}).update(updates)
        state["date"] = today
        save_state(state)

if __name__ == "__main__":
    main()
