import os
import requests
from bs4 import BeautifulSoup
from telegram import Bot, ParseMode

BOT_TOKEN = os.getenv("BOT_TOKEN")
GROUP_CHAT_ID = os.getenv("GROUP_CHAT_ID")
TARGET_URL = os.getenv("TARGET_URL", "https://satta-king-fixed-no.in/")

bot = Bot(token=BOT_TOKEN)

def fetch_results():
    try:
        headers = {"User-Agent": "Mozilla/5.0"}
        r = requests.get(TARGET_URL, headers=headers, timeout=15)
        r.raise_for_status()
        soup = BeautifulSoup(r.text, "html.parser")

        games = soup.select("p.livegame")
        results = soup.select("p.liveresult")

        data = []
        for g, r in zip(games, results):
            game = g.get_text(strip=True)
            res = r.get_text(strip=True)
            data.append(f"{game}: {res}")

        return "\n".join(data)
    except Exception as e:
        print("Error:", e)
        return None

def send_to_group(text):
    try:
        bot.send_message(chat_id=GROUP_CHAT_ID, text=text, parse_mode=ParseMode.HTML)
        print("Message sent.")
    except Exception as e:
        print("Telegram error:", e)

if __name__ == "__main__":
    results = fetch_results()
    if results:
        msg = f"📢 <b>Satta King Live Results</b>\n\n{results}\n\n🔗 {TARGET_URL}"
        send_to_group(msg)
    else:
        print("No results found.")
