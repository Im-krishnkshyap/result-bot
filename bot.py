import os
import json
import requests
import time
from datetime import datetime, timedelta
from bs4 import BeautifulSoup

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")
STATE_FILE = "last_sent.json"

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

HINDI_NAMES = {
    "DELHI BAZAR": "दिल्ली बाजार",
    "SHRI GANESH": "श्री गणेश",
    "FARIDABAD": "फरीदाबाद",
    "GHAZIYABAD": "गाजियाबाद",
    "GALI": "गली",
    "DISAWER": "दिसावर"
}

# ---------------- UTILITY ----------------
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
            return json.load(f)
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
    try:
        requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text})
    except Exception as e:
        print("❌ Telegram error:", e)

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
    for g in TARGETS:
        if g in updates:
            hn = HINDI_NAMES[g]
            lines.append(f"{hn:12} {updates[g]}")
    lines.append("√√√√√√√√√√√√√√√√√")
    return "\n".join(lines)

# ---------------- MAIN LOOP ----------------
def main():
    while True:
        now = datetime.now()
        today = now.strftime("%d-%m")
        yesterday = (now - timedelta(days=1)).strftime("%d-%m")

        state = load_state()
        soup = fetch_html()

        # नया दिन reset + fallback (कल का पूरा result)
        if state.get("date") != today:
            yres = parse_chart_for_date(soup, yesterday)
            if yres:
                msg = build_message(yesterday, yres)
                send_message(msg)
            state = {"date": today, "sent_results": {}}
            save_state(state)

        # आज के result निकालो
        todays_live = parse_live(soup)
        todays_chart = parse_chart_for_date(soup, today)

        final_results = {}
        for g in TARGETS:
            if g in todays_live:
                final_results[g] = todays_live[g]
            elif g in todays_chart:
                final_results[g] = todays_chart[g]

        # सिर्फ नए updates भेजो
        updates = {}
        for g, val in final_results.items():
            if g not in state.get("sent_results", {}) or state["sent_results"][g] != val:
                updates[g] = val

        if updates:
            msg = build_message(today, updates)
            send_message(msg)
            state["sent_results"].update(updates)
            state["date"] = today
            save_state(state)

        time.sleep(60)  # हर 1 मिनट बाद check

if __name__ == "__main__":
    main()
