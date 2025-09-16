# bot.py
import requests, os, re, sys
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GAZIYABAD", "GALI", "DESAWAR"]

def canonical_name(raw):
    s = raw.upper().strip()
    if "DELHI" in s and "BAZAR" in s: return "DELHI BAZAR"
    if "SHRI" in s and "GANESH" in s: return "SHRI GANESH"
    if "FARIDABAD" in s: return "FARIDABAD"
    if "GAZIYABAD" in s or "GHAZIYABAD" in s: return "GAZIYABAD"
    if "GALI" in s: return "GALI"
    if "DISAWER" in s or "DESAWAR" in s: return "DESAWAR"
    return s

def extract_num(text):
    if not text: return None
    m = re.search(r'\d{1,3}', text)
    return m.group(0) if m else None

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(api, data=payload, timeout=10)
        print("Telegram send:", r.status_code, r.text)
    except Exception as e:
        print("Send fail:", e, file=sys.stderr)

def main():
    html = requests.get(URL, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    games = soup.select(".resultmain .livegame")
    vals  = soup.select(".resultmain .liveresult")

    final = {}
    for i, g in enumerate(games):
        name = canonical_name(g.get_text())
        if name in TARGETS and i < len(vals):
            num = extract_num(vals[i].get_text())
            if num: final[name] = num

    if not final:
        print("⚠️ No live results found")
        return

    lines = ["*🔛खबर की जानकारी👉*", "*⚠️⚠️⚠️⚠️⚠️⚠️〽️〽️*"]
    for t in TARGETS:
        if t in final:
            lines.append(f"*{t}:* {final[t]}")
    msg = "\n".join(lines)

    print("Sending:\n", msg)
    send_message(msg)

if __name__ == "__main__":
    main()
