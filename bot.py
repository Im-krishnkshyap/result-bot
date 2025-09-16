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
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN or CHAT_ID not set")
        return
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg, "parse_mode": "Markdown"}
    try:
        r = requests.post(api, data=payload, timeout=10)
        print("Telegram send:", r.status_code, r.text)
    except Exception as e:
        print("Send fail:", e, file=sys.stderr)

def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals  = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        name = canonical_name(g.get_text())
        if i < len(vals):
            num = extract_num(vals[i].get_text())
            if num: results[name] = num
    return results

def parse_chart(soup):
    results = {}
    # पहली chart table (जिसमें Faridabad, Ghaziabad, Gali, Disawar etc.)
    rows = soup.select("table.newtable tr")
    if not rows: return results
    last = rows[-1].find_all("td")   # सबसे नीचे वाली row (latest date)
    headers = [h.get_text().strip().upper() for h in rows[0].find_all("th")]
    for i, h in enumerate(headers):
        cname = canonical_name(h)
        if cname in TARGETS and i < len(last):
            num = extract_num(last[i].get_text())
            if num: results[cname] = num
    return results

def main():
    html = requests.get(URL, timeout=10).text
    soup = BeautifulSoup(html, "html.parser")

    live = parse_live(soup)
    chart = parse_chart(soup)

    final = {}
    for t in TARGETS:
        if t in live:
            final[t] = live[t]
        elif t in chart:
            final[t] = chart[t]
        else:
            final[t] = "WAIT"

    lines = ["*🔛खबर की जानकारी👉*", "*⚠️⚠️⚠️⚠️⚠️⚠️〽️〽️*"]
    for t in TARGETS:
        lines.append(f"*{t}:* {final[t]}")
    msg = "\n".join(lines)

    print("Sending:\n", msg)
    send_message(msg)

if __name__ == "__main__":
    main()
