import os
import json
import time
from datetime import datetime, timedelta
import requests
from bs4 import BeautifulSoup

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

SLOTS = {
    "DELHI BAZAR": ("15:14", "15:20"),
    "SHRI GANESH": ("16:47", "17:00"),
    "FARIDABAD": ("18:14", "18:20"),
    "GHAZIYABAD": ("22:10", "22:20"),
    "GALI": ("00:00", "00:05"),
    "DISAWER": ("05:14", "05:20"),
}

# ---------------- UTILITY ----------------
def canonical_name(raw):
    s = raw.upper().strip()
    if "DELHI BAZAR" in s: return "DELHI BAZAR"
    if "SHRI" in s and "GANESH" in s: return "SHRI GANESH"
    if "FARIDABAD" in s: return "FARIDABAD"
    if "GHAZI" in s or "GAZI" in s: return "GHAZIYABAD"
    if s == "GALI" or s.startswith("GALI ") or s.endswith(" GALI") or s == "GALI (GL)": return "GALI"
    if "DISAWER" in s or "DESAWAR" in s: return "DISAWER"
    return s

def extract_num(text):
    t = text.strip()
    if t.upper() == "WAIT" or t == "":
        return None
    return t if t.isdigit() else None

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"date": None, "sent_results": {}, "slot_done": {}}
    try:
        with open(STATE_FILE, "r") as f:
            return json.load(f)
    except Exception:
        return {"date": None, "sent_results": {}, "slot_done": {}}

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

# ---------------- PARSING ----------------
def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        cname = canonical_name(g.get_text())
        if cname in TARGETS and i < len(vals):
            num = extract_num(vals[i].get_text())
            if num:
                results[cname] = num
    return results

def parse_chart_for_date(soup, date_str):
    results = {}
    tables = soup.select("table.newtable")
    for table in tables:
        rows = table.select("tr")
        if not rows:
            continue
        headers = [h.get_text().strip().upper() for h in rows[0].find_all(["th","td"])]
        for row in rows[1:]:
            cols = row.find_all(["td","th"])
            if not cols:
                continue
            if cols[0].get_text().strip() == date_str:
                for i, h in enumerate(headers):
                    cname = canonical_name(h)
                    if cname in TARGETS and i < len(cols):
                        num = extract_num(cols[i].get_text())
                        if num:
                            results[cname] = num
                break
    return results

def build_message(date_str, updates):
    lines = [f"🔛खबर की जानकारी😘", f"📅 {date_str} का अपडेट"]
    order = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]
    for g in order:
        if g in updates:
            v = updates[g]
            if g == "DELHI BAZAR":
                lines.append(f"दिल्ली बाजार   {v}")
            elif g == "SHRI GANESH":
                lines.append(f"श्री गणेश          {v}")
            elif g == "FARIDABAD":
                lines.append(f"फरीदाबाद        {v}")
            elif g == "GHAZIYABAD":
                lines.append(f"गाजियाबाद      {v}")
            elif g == "GALI":
                lines.append(f"गली                {v}")
            elif g == "DISAWER":
                lines.append(f"दिसावर            {v}")
    lines.append("√√√√√√√√√√√√√√√√√")
    return "\n".join(lines)

# ---------------- MAIN LOOP ----------------
def main():
    while True:
        now = datetime.now()
        today = now.strftime("%d-%m")
        state = load_state()

        # Reset state at new day
        if state.get("date") != today:
            state = {"date": today, "sent_results": {}, "slot_done": {}}
            save_state(state)

        # Check each slot
        for game, (start, end) in SLOTS.items():
            start_time = datetime.strptime(start, "%H:%M").time()
            end_time = datetime.strptime(end, "%H:%M").time()
            if start_time <= now.time() <= end_time:
                if not state["slot_done"].get(game):
                    soup = fetch_html()
                    results = parse_live(soup)
                    chart = parse_chart_for_date(soup, today)
                    final = results.get(game) or chart.get(game)
                    if final:
                        msg = build_message(today, {game: final})
                        send_message(msg)
                        state["sent_results"][game] = final
                        state["slot_done"][game] = True
                        save_state(state)

        # After Disawar slot, send summary
        disawar_end = datetime.strptime("05:20", "%H:%M").time()
        if now.time() > disawar_end and not state.get("summary_sent"):
            if len(state["sent_results"]) == len(TARGETS):
                msg = build_message(today, state["sent_results"])
                send_message(msg)
                state["summary_sent"] = True
                save_state(state)

        time.sleep(60)  # check every minute

if __name__ == "__main__":
    main()
