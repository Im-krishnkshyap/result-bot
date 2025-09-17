import os
import json
import requests
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import time  # नया इम्पोर्ट: स्लीप के लिए

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

# टाइमिंग्स 24-घंटे फॉर्मेट में (HH:MM)
TIMINGS = {
    "DELHI BAZAR": "15:01",
    "SHRI GANESH": "16:30",
    "FARIDABAD": "18:00",
    "GHAZIYABAD": "21:25",
    "GALI": "23:25",
    "DISAWER": "04:50"
}

# ------------------ Utility ------------------

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

def process_results():
    today = datetime.now().strftime("%d-%m")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m")
    state = load_state()
    soup = fetch_html()

    # नया दिन → कल का पूरा result भेजो (fallback)
    if state.get("date") != today:
        yres = parse_chart_for_date(soup, yesterday)
        if yres:
            msg = build_message(yesterday, yres)
            send_message(msg)
        state = {"date": today, "sent_results": {}}
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

    # अपडेट्स चेक करो
    updates = {}
    for g, val in final_results.items():
        if g not in state.get("sent_results", {}) or state["sent_results"][g] != val:
            updates[g] = val

    # अगर कुछ अपडेट है → भेजो
    if updates:
        msg = build_message(today, updates)
        send_message(msg)
        state.setdefault("sent_results", {}).update(updates)
        state["date"] = today
        save_state(state)

def main():
    while True:
        now = datetime.now()
        min_delta = timedelta(days=1)
        for timestr in TIMINGS.values():
            h, m = map(int, timestr.split(':'))
            target = now.replace(hour=h, minute=m, second=0, microsecond=0)
            if target <= now:  # अगर पास्ट है, तो नेक्स्ट डे
                target += timedelta(days=1)
            delta = target - now
            if delta < min_delta:
                min_delta = delta
        sleep_seconds = max(min_delta.total_seconds(), 0)
        print(f"स्लीप कर रहा हूँ {sleep_seconds} सेकंड्स तक...")  # डीबग के लिए
        time.sleep(sleep_seconds)
        process_results()  # अब प्रोसेस करो

if __name__ == "__main__":
    main()