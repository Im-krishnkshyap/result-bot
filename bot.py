import requests
from bs4 import BeautifulSoup
import os

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = "https://satta-king-fixed-no.in"  # Original site link

# जिन games का result चाहिए
TARGETS = ["DELHI BAZAR", "SHRI GANESH", "FARIDABAD", "GAZIYABAD", "GALI", "DISAWER"]

def send_message(msg):
    api_url = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    payload = {"chat_id": CHAT_ID, "text": msg}
    requests.post(api_url, data=payload)

def check_results():
    res = requests.get(URL, timeout=10)
    soup = BeautifulSoup(res.text, "html.parser")

    results = {}
    # full boards
    for block in soup.select(".gboardfull"):
        name = block.select_one(".gbfullgamename")
        value = block.select_one(".gbfullresult")
        if name and value:
            game = name.text.strip().upper()
            result = value.text.replace("{","").replace("}","").strip()
            if game in [t.upper() for t in TARGETS] and result:
                results[game] = result

    # half boards
    for block in soup.select(".gboardhalf"):
        name = block.select_one(".gbgamehalf")
        value = block.select_one(".gbhalfresulto")
        if name and value:
            game = name.text.strip().upper()
            result = value.text.replace("{","").replace("}","").strip()
            if game in [t.upper() for t in TARGETS] and result:
                results[game] = result

    return results

if __name__ == "__main__":
    found = check_results()
    if found:
        msg = "📊 Latest Results:\n" + "\n".join([f"{k}: {v}" for k,v in found.items()])
        send_message(msg)
