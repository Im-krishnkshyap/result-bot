# bot.py
import requests
from bs4 import BeautifulSoup
import os
import re
import sys

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

# User-targets (canonical names you want in final message)
WANTED = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GAZIYABAD", "GALI", "DESAWAR"]

HEADERS = {
    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
                  "(KHTML, like Gecko) Chrome/120.0 Safari/537.36"
}

def canonical_name(raw: str) -> str:
    if not raw:
        return ""
    s = raw.upper()
    # remove parentheses content like "(DL)"
    s = re.sub(r'\(.*?\)', ' ', s)
    # remove non-alphanumeric except space
    s = re.sub(r'[^A-Z0-9 ]+', ' ', s)
    # collapse spaces
    s = re.sub(r'\s+', ' ', s).strip()
    # map common variants to canonical names
    if 'DISAWER' in s or 'DESAWAR' in s:
        return 'DESAWAR'
    if 'DELHI' in s and 'BAZAR' in s:
        return 'DELHI BAZAR'
    if 'SHRI' in s and 'GANESH' in s:
        return 'SHRI GANESH'
    if 'FARIDABAD' in s:
        return 'FARIDABAD'
    if 'GAZIYABAD' in s or 'GHAZIYABAD' in s:
        return 'GAZIYABAD'
    if 'GALI' in s:
        return 'GALI'
    return s

def extract_value(text: str):
    if not text:
        return None
    # find first standalone number (1-3 digits)
    m = re.search(r'\b(\d{1,3})\b', text)
    return m.group(1) if m else None

def send_message(msg: str):
    if not BOT_TOKEN or not CHAT_ID:
        print("BOT_TOKEN or CHAT_ID not set in env. Exiting.", file=sys.stderr)
        return
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    try:
        r = requests.post(api_url, data=payload, timeout=10)
        print("Telegram send status:", r.status_code, r.text)
    except Exception as e:
        print("Telegram send failed:", e, file=sys.stderr)

def parse_live_section(soup):
    results = {}
    live_games = soup.select('.resultmain .livegame')
    live_vals  = soup.select('.resultmain .liveresult')
    for i, g in enumerate(live_games):
        name_raw = g.get_text(separator=' ').strip()
        name = canonical_name(name_raw)
        val_text = live_vals[i].get_text(separator=' ').strip() if i < len(live_vals) else ""
        value = extract_value(val_text)
        if value:
            results[name] = value
    return results

def parse_boards(soup):
    results = {}
    # iterate in DOM order to prefer nearer-to-top blocks
    for block in soup.select('.gboardfull, .gboardhalf'):
        # find name element
        name_el = block.select_one('.gbfullgamename') or block.select_one('.gbgamehalf')
        if not name_el:
            continue
        name = canonical_name(name_el.get_text())
        # try to extract number from whole block text (covers many classes)
        text = block.get_text(separator=' ')
        value = extract_value(text)
        if value:
            # keep first seen if not already recorded (we prefer top/live first)
            if name not in results:
                results[name] = value
    return results

def main():
    try:
        r = requests.get(URL, headers=HEADERS, timeout=10)
        r.raise_for_status()
    except Exception as e:
        print("Failed to fetch URL:", e, file=sys.stderr)
        return

    soup = BeautifulSoup(r.text, "html.parser")

    # 1) first try top live section
    live = parse_live_section(soup)
    # 2) fallback to board blocks
    boards = parse_boards(soup)

    # merge with priority: live > boards
    final = {}
    for target in WANTED:
        if target in live:
            final[target] = live[target]
        elif target in boards:
            final[target] = boards[target]

    if not final:
        print("No target results found. Parsed live keys:", list(live.keys()), "board keys:", list(boards.keys()))
        return

    # format message
    lines = ["📊 Latest Results:"]
    for t in WANTED:
        if t in final:
            lines.append(f"{t}: {final[t]}")
    msg = "\n".join(lines)
    print("Sending message:\n", msg)
    send_message(msg)

if __name__ == "__main__":
    main()
