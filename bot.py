import os
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")
LOCK_FILE = "bot_lock.txt"

STATE_FILE = "last_sent.json"

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

TIMINGS = {
    "DELHI BAZAR": "14:50",
    "SHRI GANESH": "16:30",
    "FARIDABAD": "18:00",
    "GHAZIYABAD": "21:25",
    "GALI": "23:25",
    "DISAWER": "04:50"
}

# ------------------ Utility ------------------

def is_locked():
    return os.path.exists(LOCK_FILE)

def lock():
    with open(LOCK_FILE, "w") as f:
        f.write("locked")

def unlock():
    if os.path.exists(LOCK_FILE):
        os.remove(LOCK_FILE)

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

# ------------------ Main ------------------

def is_due_time():
    now = datetime.now()
    for timestr in TIMINGS.values():
        h, m = map(int, timestr.split(':'))
        target = now.replace(hour=h, minute=m, second=0, microsecond=0)
        if now - target < timedelta(minutes=5) and now > target:  # 5 मिनट विंडो में है
            return True
    return False

def main():
    if is_locked():
        print("लॉक है, स्किप!")
        return
    lock()
    try:
        if not is_due_time():
            print("कोई टाइमिंग ड्यू नहीं, स्किप!")
            return
        today = datetime.now().strftime("%d-%m")
        yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m")
        state = load_state()
        soup = fetch_html()

        if state.get("date") != today:
            yres = parse_chart_for_date(soup, yesterday)
            if yres:
                msg = build_message(yesterday, yres)
                send_message(msg)
            state = {"date": today, "sent_results": {}}
            save_state(state)

        todays_live = parse_live(soup)
        todays_chart = parse_chart_for_date(soup, today)

        final_results = {}
        for g in TARGETS:
            if g in todays_live:
                final_results[g] = todays_live[g]
            elif g in todays_chart:
                final_results[g] = todays_chart[g]

        updates = {}
        for g, val in final_results.items():
            if g not in state.get("sent_results", {}) or state["sent_results"][g] != val:
                updates[g] = val

        if updates:
            msg = build_message(today, updates)
            send_message(msg)
            state.setdefault("sent_results", {}).update(updates)
            state["date"] = today
            save_state(state)
    finally:
        unlock()

if __name__ == "__main__":
    main()
