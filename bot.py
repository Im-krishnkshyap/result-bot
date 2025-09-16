import os
import json
import requests
from datetime import datetime, time
from bs4 import BeautifulSoup
import time as t

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = "https://satta-king-fixed-no.in"

STATE_FILE = "last_sent.json"

# Targets
TARGETS = ["DELHI BAZAR (DL)", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

# Refresh schedule (HH:MM start, HH:MM end)
REFRESH_TIMES = {
    "DELHI BAZAR (DL)": (time(3,14), time(3,20)),
    "SHRI GANESH": (time(4,45), time(4,50)),
    "FARIDABAD": (time(6,14), time(6,20)),
    "GHAZIYABAD": (time(10,5), time(10,15)),
    "GALI": (time(12,0), time(12,5)),
    "DISAWER": (time(17,15), time(17,20))
}

# ------------------ Utilities ------------------

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text})

def load_state():
    if not os.path.exists(STATE_FILE):
        return {}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except:
        return {}

def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)

def fetch_live_html():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        name = g.get_text().strip().upper()
        if name in TARGETS and i < len(vals):
            val = vals[i].get_text().strip()
            results[name] = val if val else "WAIT"
    return results

def build_message(results):
    lines = []
    for g in TARGETS:
        val = results.get(g, "WAIT")
        lines.append(f"{g} → {val}")
    return "\n".join(lines)

# ------------------ Main Loop ------------------

def main():
    state = load_state()
    
    while True:
        now = datetime.now().time()
        soup = fetch_live_html()
        live_results = parse_live(soup)
        updates = {}

        for g in TARGETS:
            start, end = REFRESH_TIMES[g]
            # केवल उस समय में check करें
            if start <= now <= end:
                val = live_results.get(g, "WAIT")
                if g not in state or state[g] != val:
                    updates[g] = val
                    state[g] = val

        # अगर कुछ अपडेट है → भेजो
        if updates:
            msg = build_message(state)
            send_message(msg)
            save_state(state)

        t.sleep(60)  # हर 1 मिनट बाद refresh

if __name__ == "__main__":
    main()
