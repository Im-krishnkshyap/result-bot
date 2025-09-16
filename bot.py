import os
import json
import requests
from bs4 import BeautifulSoup
from datetime import datetime, timedelta

# ==========================
# CONFIG
# ==========================
RESULT_URL = os.getenv("RESULT_URL", "https://example.com/chart")  # यहां अपना chart URL डालो
STATE_FILE = "last_sent.json"

TARGETS = [
    "DELHI BAZAR",
    "SHRI GANESH",
    "FARIDABAD",
    "GHAZIYABAD",
    "GALI",
    "DISAWER"
]

# ==========================
# HELPERS
# ==========================

def load_state():
    if not os.path.exists(STATE_FILE):
        return {"date": None, "sent_results": {}}
    try:
        with open(STATE_FILE, "r") as f:
            data = json.load(f)
            if not isinstance(data, dict):
                return {"date": None, "sent_results": {}}
            if "date" not in data:
                data["date"] = None
            if "sent_results" not in data:
                data["sent_results"] = {}
            return data
    except Exception:
        return {"date": None, "sent_results": {}}


def save_state(state):
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def fetch_html():
    r = requests.get(RESULT_URL, timeout=20)
    r.raise_for_status()
    return BeautifulSoup(r.text, "html.parser")


def parse_chart_for_date(soup, date_str):
    """
    Table parse करो और दिए गए date_str (DD-MM) का result निकालो
    """
    results = {}
    try:
        rows = soup.find_all("tr")
        for row in rows:
            cols = row.find_all(["th", "td"])
            if len(cols) < 2:
                continue

            # Example: <th> DELHI BAZAR(DL) </th>
            name = cols[0].get_text(strip=True).upper()
            value = cols[1].get_text(strip=True).upper()

            if not name or not value:
                continue

            results[name] = value
    except Exception as e:
        print("Parse error:", e)

    # Debug print
    print("DEBUG parse_chart_for_date:", date_str, results)
    return results


def build_message(date_str, results):
    """
    Message बनाओ selected TARGETS के लिए
    """
    lines = [f"📅 {date_str} का रिज़ल्ट"]
    for g in TARGETS:
        found = None
        for key, val in results.items():
            if g.lower() in key.lower():   # fuzzy match
                found = val
                break
        if found:
            lines.append(f"{g} → {found}")
        else:
            lines.append(f"{g} → WAIT")
    return "\n".join(lines)


# ==========================
# MAIN
# ==========================

def main():
    today = datetime.now().strftime("%d-%m")
    yesterday = (datetime.now() - timedelta(days=1)).strftime("%d-%m")

    state = load_state()

    soup = fetch_html()

    # Get yesterday & today results
    yres = parse_chart_for_date(soup, yesterday)
    tres = parse_chart_for_date(soup, today)

    ymsg = build_message(yesterday, yres)
    tmsg = build_message(today, tres)

    print("\n==== FINAL MESSAGES ====")
    print(ymsg)
    print("------------------------")
    print(tmsg)

    # Save state (example logic)
    state["date"] = today
    state["sent_results"][today] = tres
    save_state(state)


if __name__ == "__main__":
    main()
