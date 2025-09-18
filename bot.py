# baba.py  -- cron-friendly single-run script (run every minute via GitHub Actions)
import os
import json
import requests
from datetime import datetime, timedelta, time as dtime
from zoneinfo import ZoneInfo
from bs4 import BeautifulSoup

# ---------------- CONFIG ----------------
BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("RESULT_URL", "https://satta-king-fixed-no.in")

STATE_FILE = "last_sent.json"
TZ = ZoneInfo("Asia/Kolkata")

TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GHAZIYABAD", "GALI", "DISAWER"]

SLOTS = {
    "DELHI BAZAR": ("15:14", "15:20"),
    "SHRI GANESH": ("16:47", "17:00"),
    "FARIDABAD": ("18:14", "18:20"),
    "GHAZIYABAD": ("22:10", "22:20"),
    "GALI": ("00:00", "00:05"),
    "DISAWER": ("05:14", "05:20"),
}

SUMMARY_CUTOFF = dtime(5, 20)   # 05:20 -- after this we can send previous-day summary

# ---------------- UTIL ----------------
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
    if text is None:
        return None
    t = text.strip()
    if t.upper() == "WAIT" or t == "":
        return None
    return t if t.isdigit() else None

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"results": {}, "slot_done": {}, "summary_sent": {}}
    try:
        with open(STATE_FILE, "r", encoding="utf-8") as f:
            return json.load(f)
    except Exception as e:
        print("Warning: could not load state:", e)
        return {"results": {}, "slot_done": {}, "summary_sent": {}}

def save_state(state):
    try:
        with open(STATE_FILE, "w", encoding="utf-8") as f:
            json.dump(state, f, indent=2, ensure_ascii=False)
    except Exception as e:
        print("Error saving state:", e)

def fetch_html():
    headers = {"User-Agent": "Mozilla/5.0 (compatible; AntaryamiBot/1.0)"}
    r = requests.get(URL, timeout=20, headers=headers)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")

def send_message(text):
    if not BOT_TOKEN or not GROUP_CHAT_ID:
        print("[DRY-RUN] would send message:\n", text)
        return
    url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    try:
        resp = requests.post(url, data={"chat_id": GROUP_CHAT_ID, "text": text}, timeout=15)
        resp.raise_for_status()
    except Exception as e:
        print("Telegram send error:", e)

# ---------------- PARSING ----------------
def parse_live(soup):
    results = {}
    games = soup.select(".resultmain .livegame")
    vals = soup.select(".resultmain .liveresult")
    for i, g in enumerate(games):
        try:
            cname = canonical_name(g.get_text())
            if cname in TARGETS and i < len(vals):
                num = extract_num(vals[i].get_text())
                if num:
                    results[cname] = num
        except Exception:
            continue
    return results

def parse_chart_for_date(soup, date_str):
    results = {}
    tables = soup.select("table.newtable")
    for table in tables:
        rows = table.select("tr")
        if not rows:
            continue
        # header -> index mapping (robust)
        header_cells = rows[0].find_all(["th", "td"])
        headers = {}
        for idx, cell in enumerate(header_cells):
            cname = canonical_name(cell.get_text())
            headers[cname] = idx
        for row in rows[1:]:
            cols = row.find_all(["td", "th"])
            if not cols:
                continue
            if cols[0].get_text().strip() == date_str:
                for cname, idx in headers.items():
                    if cname in TARGETS and idx < len(cols):
                        num = extract_num(cols[idx].get_text())
                        if num:
                            results[cname] = num
                break
    return results

def build_message(date_str, updates, prefix=None):
    lines = []
    if prefix:
        lines.append(prefix)
    lines += [f"🔛खबर की जानकारी😘", f"📅 {date_str} का अपडेट"]
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

# ---------------- HELPERS ----------------
def parse_time_str(tstr):
    hh, mm = map(int, tstr.split(":"))
    return dtime(hh, mm)

def time_in_range(start, end, now_t):
    # inclusive range (handles start <= end only, our slots do not wrap midnight)
    return start <= now_t <= end

# ---------------- MAIN (single run) ----------------
def main():
    now = datetime.now(TZ)
    now_time = now.time()

    # collection_date logic:
    # If current time <= SUMMARY_CUTOFF (05:20), treat current runs as still collecting previous day
    if now_time <= SUMMARY_CUTOFF:
        collection_date = (now - timedelta(days=1)).date()
    else:
        collection_date = now.date()
    collection_date_str = collection_date.strftime("%d-%m")

    prev_date = collection_date - timedelta(days=1)
    prev_date_str = prev_date.strftime("%d-%m")

    print(f"[{now.isoformat()}] collection_date={collection_date_str} (now_time={now_time})")

    state = load_state()
    state.setdefault("results", {})
    state.setdefault("slot_done", {})
    state.setdefault("summary_sent", {})

    # Ensure dicts exist for collection_date
    state["results"].setdefault(collection_date_str, {})
    state["slot_done"].setdefault(collection_date_str, {})

    # Try fetch once only when a slot is active
    try:
        soup = fetch_html()
    except Exception as e:
        print("Fetch error:", e)
        soup = None

    # Check current active slot(s) by time and attempt to fetch result for collection_date
    for game, (start_s, end_s) in SLOTS.items():
        start_t = parse_time_str(start_s)
        end_t = parse_time_str(end_s)
        if time_in_range(start_t, end_t, now_time):
            # if slot already done for this date, skip
            if state["slot_done"].get(collection_date_str, {}).get(game):
                print(f"Slot already done for {game} on {collection_date_str}")
                continue
            print(f"Active slot: {game} ({start_s} - {end_s}) for date {collection_date_str}")
            final = None
            if soup:
                try:
                    live = parse_live(soup)
                    chart = parse_chart_for_date(soup, collection_date_str)
                    # prefer live, fallback to chart
                    final = live.get(game) or chart.get(game)
                except Exception as e:
                    print("Parse error for", game, e)
            else:
                print("No HTML to parse for", game)

            if final:
                msg = build_message(collection_date_str, {game: final})
                send_message(msg)
                # save
                state["results"].setdefault(collection_date_str, {})[game] = final
                state["slot_done"].setdefault(collection_date_str, {})[game] = True
                save_state(state)
                print(f"Sent {game}={final} for {collection_date_str}")
            else:
                print(f"No final value yet for {game} at {now_time}")

    # After SUMMARY_CUTOFF (05:20), attempt to send summary for previous calendar day (prev_date)
    if now_time > SUMMARY_CUTOFF:
        # prev_date_str is the day that JUST finished
        if not state.get("summary_sent", {}).get(prev_date_str):
            results_for_prev = state.get("results", {}).get(prev_date_str, {})
            # Build summary — include missing keys as 'WAIT' or '-' if you prefer
            summary_map = {}
            for g in TARGETS:
                summary_map[g] = results_for_prev.get(g, "WAIT")
            # Only send summary if at least one result exists (optional policy)
            if any(v != "WAIT" for v in summary_map.values()):
                msg = build_message(prev_date_str, {k:v for k,v in summary_map.items() if v != "WAIT"})
                # Add prefix to indicate summary
                send_message("🕉Antaryami Baba🕉:\n" + msg)
                state.setdefault("summary_sent", {})[prev_date_str] = True
                save_state(state)
                print(f"Summary sent for {prev_date_str}")
            else:
                print(f"No results available to summarize for {prev_date_str} yet.")
        else:
            print(f"Summary already sent for {prev_date_str}")

    # clean up very old dates (optional): keep last 7 days
    try:
        keep = set([(now.date() - timedelta(days=i)).strftime("%d-%m") for i in range(0,8)])
        state["results"] = {k:v for k,v in state["results"].items() if k in keep}
        state["slot_done"] = {k:v for k,v in state["slot_done"].items() if k in keep}
        state["summary_sent"] = {k:v for k,v in state["summary_sent"].items() if k in keep}
        save_state(state)
    except Exception:
        pass

if __name__ == "__main__":
    main()
