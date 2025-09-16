import os
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ------------------ Config ------------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
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
        return {"date": None, "sent_results": {}, "fallback_sent": False}
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"date": None, "sent_results": {}, "fallback_sent": False}
            return data
    except Exception:
        return {"date": None, "sent_results": {}, "fallback_sent": False}

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

def build_message(date_str, updates):
    lines = [f"📅 {date_str} का अपडेट"]
    for g, v in updates.items():
        lines.append(f"{g} → {v}")
    return "\n".join(lines)

# ------------------ Main ------------------
def main():
    today = datetime.now().strftime("%d-%m")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m")
    state = load_state()
    soup = fetch_html()

    # ---------- Fallback: अगर date बदल गया और कल का result missed ----------
    if state.get("date") != today and not state.get("fallback_sent", False):
        yres = parse_chart_for_date(soup, yesterday)
        if yres:
            msg = build_message(yesterday, yres)
            send_message(msg)
        state = {"date": today, "sent_results": {}, "fallback_sent": True}
        save_state(state)

    # आज के live और chart results
    todays_live = parse_live(soup)
    todays_chart = parse_chart_for_date(soup, today)

    # Merge: live > chart
    final_results = {}
    for g in TARGETS:
        if g in todays_live:
            final_results[g] = todays_live[g]
        elif g in todays_chart:
            final_results[g] = todays_chart[g]

    # ---------- Updates check ----------
    updates = {}
    for g, val in final_results.items():
        prev_val = state.get("sent_results", {}).get(g)
        if prev_val != val:
            updates[g] = val

    # ---------- Send updates ----------
    if updates:
        msg = build_message(today, updates)
        send_message(msg)
        state.setdefault("sent_results", {}).update(updates)
        state["date"] = today
        save_state(state)

if __name__ == "__main__":
    main()
