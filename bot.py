import os
import requests
from bs4 import BeautifulSoup

BOT_TOKEN = os.getenv("BOT_TOKEN")
CHAT_ID = os.getenv("GROUP_CHAT_ID")
URL = os.getenv("TARGET_URL")

def scrape_results():
    r = requests.get(URL, timeout=10)
    r.raise_for_status()
    soup = BeautifulSoup(r.text, "html.parser")

    # टेबल या div से रिज़ल्ट निकालो (यह selector website के हिसाब से बदलना होगा)
    result_table = soup.find("table", class_="resultTable")
    results = []
    if result_table:
        rows = result_table.find_all("tr")
        for row in rows:
            cols = row.find_all("td")
            if len(cols) >= 2:
                market = cols[0].get_text(strip=True)
                number = cols[1].get_text(strip=True)
                results.append(f"{market} === {number}")
    
    # अगले आने वाले रिज़ल्ट के लिए placeholder
    next_result = "आने वाला == wait..."
    
    # टेक्स्ट तैयार करना
    final_text = "📢 खबर की जानकारी👇\n\n"
    final_text += "\n".join(results)
    final_text += f"\n\n{next_result}\n\n🙏 Antaryami Baba"
    
    return final_text

def send_message(msg):
    api = f"https://api.telegram.org/bot{BOT_TOKEN}/sendMessage"
    data = {"chat_id": CHAT_ID, "text": msg}
    requests.post(api, data=data)

if __name__ == "__main__":
    text = scrape_results()
    send_message(text[:4000])
