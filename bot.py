import os
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"

# Game Targets
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

def fetch_html():
    r = requests.get(URL, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def send_message(text):
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text})

# ------------------ Parsing ------------------

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

def build_message(date_str, results, fallback=False):
    lines = [f"📅 {date_str} का रिज़ल्ट"]
    for g in TARGETS:
        if g in results:
            lines.append(f"{g} → {results[g]}")
        else:
            lines.append(f"{g} → {'WAIT' if not fallback else 'NA'}")
    return "\n".join(lines)

# ------------------ Main ------------------

def main():
    today = datetime.now().strftime("%d-%m")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m")
    state = load_state()

    soup = fetch_html()

    # 1️⃣ नया दिन → कल का पूरा result भेजो
    if state["date"] != today:
        yres = parse_chart_for_date(soup, yesterday)
        if yres:
            msg = build_message(yesterday, yres, fallback=True)
            send_message(msg)
        state = {"date": today, "sent_results": {}}
        save_state(state)

    # 2️⃣ आज का live chart parse करो
    todays_live = parse_live(soup)
    todays_chart = parse_chart_for_date(soup, today)

    # 3️⃣ Delhi Bazar(DL) आने तक कोई live msg मत भेजो
    if "DELHI BAZAR" not in todays_live:
        return

    # 4️⃣ Delhi Bazar आने के बाद send/update
    final_results = state.get("sent_results", {}).copy()
    updated = False

    # Merge priority: live > chart
    for g in TARGETS:
        new_val = None
        if g in todays_live:
            new_val = todays_live[g]
        elif g in todays_chart:
            new_val = todays_chart[g]

        if new_val and final_results.get(g) != new_val:
            final_results[g] = new_val
            updated = True

    if updated:
        msg = build_message(today, final_results)
        send_message(msg)
        state["sent_results"] = final_results
        state["date"] = today
        save_state(state)

if __name__ == "__main__":
    main()
